import http from './index'
import type { ApiResponse, PracticeSession, PracticeMessage, ChatEvent } from '@/types'

function unwrapResponse<T>(request: Promise<unknown>) {
  return request as Promise<ApiResponse<T>>
}

/**
 * Practice (AI 话术演练) API
 */
export const practiceApi = {
  /**
   * Create a new practice session
   */
  createSession(moduleCode: string, title?: string) {
    return unwrapResponse<{ session_id: number; module_code: string; title: string }>(
      http.post('/practice/sessions', { module_code: moduleCode, title: title || '话术演练' })
    )
  },

  /**
   * List practice sessions
   */
  getSessions(page = 1, pageSize = 20, moduleCode?: string, status?: string) {
    return unwrapResponse<{
      total: number
      page: number
      page_size: number
      items: PracticeSession[]
    }>(
      http.get('/practice/sessions', { params: { page, page_size: pageSize, module_code: moduleCode, status } })
    )
  },

  /**
   * Get session detail with messages
   */
  getSessionDetail(sessionId: number) {
    return unwrapResponse<{ session: PracticeSession; messages: PracticeMessage[] }>(
      http.get(`/practice/sessions/${sessionId}`)
    )
  },

  /**
   * Delete a session
   */
  deleteSession(sessionId: number) {
    return unwrapResponse<null>(http.delete(`/practice/sessions/${sessionId}`))
  },

  /**
   * Complete a session
   */
  completeSession(sessionId: number) {
    return unwrapResponse<PracticeSession>(http.post(`/practice/sessions/${sessionId}/complete`))
  },

  /**
   * Send a message and receive SSE stream.
   *
   * Returns an AbortController for cancellation and calls onEvent for each
   * parsed SSE event.
   *
   * SSE event types:
   *   - text: partial token { content: string }
   *   - tool_call: { name: string, arguments: string }
   *   - tool_result: { tool_call_id: string, content: string }
   *   - evaluation: { score, max_score, feedback, highlights, improvements }
   *   - error: { message: string }
   *   - done: { session_id, turn, average_score }
   */
  sendMessage(
    sessionId: number,
    message: string,
    onEvent: (event: ChatEvent) => void,
    onError?: (error: Error) => void,
    onDone?: () => void,
  ): AbortController {
    const controller = new AbortController()
    const token = localStorage.getItem('auth-token') || ''

    const baseUrl = '/api/v1'

    fetch(`${baseUrl}/practice/sessions/${sessionId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const errorText = await response.text().catch(() => 'Unknown error')
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('Response body is not readable')
        }

        const decoder = new TextDecoder()
        let buffer = ''

        // SSE parsing state (declared outside while for post-loop flush)
        let currentEvent = ''
        let currentData = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // Parse SSE events from buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              currentData = line.slice(6)
              // Complete event
              if (currentEvent) {
                try {
                  const data = JSON.parse(currentData)
                  onEvent({ type: currentEvent as ChatEvent['type'], data })
                } catch {
                  // Skip malformed JSON
                }
              }
              currentEvent = ''
              currentData = ''
            }
            // Empty line = event boundary, already handled by the above
          }
        }

        // Process any remaining data in buffer
        if (buffer.trim() && currentEvent) {
          try {
            const remainingData = buffer.trim()
            if (remainingData.startsWith('data: ')) {
              const data = JSON.parse(remainingData.slice(6))
              onEvent({ type: currentEvent as ChatEvent['type'], data })
            }
          } catch {
            // Skip
          }
        }
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          onError?.(error)
        }
      })
      .finally(() => {
        onDone?.()
      })

    return controller
  },
}
