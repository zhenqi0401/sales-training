import http from './index'
import type { ApiResponse } from '@/types'

function unwrapResponse<T>(request: Promise<unknown>) {
  return request as Promise<ApiResponse<T>>
}

export const salesApi = {
  getDashboard() {
    return unwrapResponse<{
      totalSales: number
      totalAudioFiles: number
      totalMethodologies: number
    }>(http.get<ApiResponse<{ totalSales: number; totalAudioFiles: number; totalMethodologies: number }>>('/sales/dashboard'))
  },

  getMethodologies(page = 1, pageSize = 20) {
    return unwrapResponse<{
      total: number
      page: number
      pageSize: number
      items: Array<{
        id: number
        title: string
        content: string
        source: string
        tags: string
        status: string
        created_at: string
      }>
    }>(http.get('/sales/methodologies', { params: { page, page_size: pageSize } }))
  },

  getMethodology(id: number) {
    return unwrapResponse<{
      id: number
      title: string
      content: string
      source: string
      tags: string
      status: string
      created_at: string
    }>(http.get(`/sales/methodologies/${id}`))
  },

  uploadAudioFile(file: File) {
    const form = new FormData()
    form.append('file', file)
    return unwrapResponse<{
      id: number
      file_url: string
      filename: string
      file_size: number
      status: string
    }>(http.post('/sales/audio-files', form))
  },

  getMyAudioFiles(page = 1, pageSize = 20) {
    return unwrapResponse<{
      total: number
      items: Array<{
        id: number
        file_url: string
        filename: string
        duration: number
        file_size: number
        status: string
        created_at: string
      }>
    }>(http.get('/sales/audio-files/my', { params: { page, page_size: pageSize } }))
  },
}
