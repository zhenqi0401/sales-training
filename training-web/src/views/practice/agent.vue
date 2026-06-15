<script setup lang="ts">
import { ref, nextTick, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { practiceApi } from '@/api/practice'
import { PRACTICE_MODULES } from '@/types'
import type { PracticeModuleConfig, PracticeMessage, PracticeEvaluation, ChatEvent } from '@/types'

const route = useRoute()
const router = useRouter()

// ── State ───────────────────────────────────────────────────────────
const moduleCode = ref<string>((route.params.moduleCode as string) || '')
const sessionId = ref<number>(0)
const sessionTitle = ref('话术演练')
const messages = ref<DisplayMessage[]>([])
const inputText = ref('')
const sending = ref(false)
const loadingSession = ref(false)
const showScenePicker = ref(true)
const controller = ref<AbortController | null>(null)
const messageListRef = ref<HTMLElement | null>(null)
const completed = ref(false)
const averageScore = ref<number | null>(null)

// ── Types ───────────────────────────────────────────────────────────
interface DisplayMessage {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'evaluation' | 'system'
  content: string
  toolCalls?: any
  toolResults?: any
  evaluation?: PracticeEvaluation
  timestamp: number
}

// ── Computed ────────────────────────────────────────────────────────
const currentModule = computed<PracticeModuleConfig | undefined>(() =>
  PRACTICE_MODULES.find(m => m.code === moduleCode.value)
)

const canSend = computed(() => inputText.value.trim() && !sending.value && !completed.value)

const sceneList = computed(() => PRACTICE_MODULES)

// ── Methods ─────────────────────────────────────────────────────────
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

function addMessage(msg: DisplayMessage) {
  messages.value.push(msg)
  scrollToBottom()
}

function updateLastAssistant(text: string) {
  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant') {
    last.content += text
  } else {
    addMessage({
      id: `asst-${Date.now()}`,
      role: 'assistant',
      content: text,
      timestamp: Date.now(),
    })
  }
  scrollToBottom()
}

function selectScene(code: string) {
  moduleCode.value = code
  showScenePicker.value = false
  startSession()
}

async function startSession() {
  loadingSession.value = true
  try {
    const res = await practiceApi.createSession(moduleCode.value)
    const data = res.data
    sessionId.value = data.session_id
    sessionTitle.value = data.title
    showScenePicker.value = false

    // Add welcome message
    const mod = currentModule.value
    const welcomeMsg = mod
      ? `你好！我是 AI 销售培训教练。\n\n当前演练场景：**${mod.title}**\n${mod.description}\n\n请用销售话术回复我，我会扮演顾客与你对话，并在每轮后给出评估。准备好了就开始吧！`
      : `你好！我是 AI 销售培训教练。请开始你的话术演练吧！`

    addMessage({
      id: 'welcome',
      role: 'assistant',
      content: welcomeMsg,
      timestamp: Date.now(),
    })
  } catch (e: any) {
    showToast(e?.message || '创建会话失败')
    showScenePicker.value = true
  } finally {
    loadingSession.value = false
  }
}

function sendMessage() {
  if (!canSend.value) return

  const text = inputText.value.trim()
  inputText.value = ''
  sending.value = true

  // Add user message
  addMessage({
    id: `user-${Date.now()}`,
    role: 'user',
    content: text,
    timestamp: Date.now(),
  })

  // Add placeholder for streaming response
  const asstId = `asst-${Date.now()}`
  addMessage({
    id: asstId,
    role: 'assistant',
    content: '',
    timestamp: Date.now(),
  })

  // Track tool calls for this turn
  let pendingToolCalls: { name: string; args: string; result?: string }[] = []

  controller.value = practiceApi.sendMessage(
    sessionId.value,
    text,
    (event: ChatEvent) => {
      switch (event.type) {
        case 'text':
          // Append text to the last assistant message
          updateLastAssistant(event.data.content || '')
          break

        case 'tool_call':
          pendingToolCalls.push({
            name: event.data.name,
            args: event.data.arguments,
          })
          // Show tool call as a compact system message
          addMessage({
            id: `tool-${Date.now()}`,
            role: 'tool',
            content: `🔧 调用工具：${event.data.name}`,
            toolCalls: event.data,
            timestamp: Date.now(),
          })
          break

        case 'tool_result':
          // Update the corresponding tool call
          const tc = pendingToolCalls.find(t => !t.result)
          if (tc) {
            tc.result = event.data.content
          }
          break

        case 'evaluation':
          const evalData = event.data as PracticeEvaluation
          addMessage({
            id: `eval-${Date.now()}`,
            role: 'evaluation',
            content: '',
            evaluation: evalData,
            timestamp: Date.now(),
          })
          break

        case 'error':
          addMessage({
            id: `error-${Date.now()}`,
            role: 'system',
            content: `❌ ${event.data.message}`,
            timestamp: Date.now(),
          })
          break

        case 'done':
          if (event.data.average_score != null) {
            averageScore.value = event.data.average_score
          }
          break
      }
    },
    (error) => {
      addMessage({
        id: `error-${Date.now()}`,
        role: 'system',
        content: `❌ 连接错误：${error.message}`,
        timestamp: Date.now(),
      })
    },
    () => {
      sending.value = false
      controller.value = null
      scrollToBottom()
    }
  )
}

function cancelSend() {
  controller.value?.abort()
  controller.value = null
  sending.value = false
}

async function finishSession() {
  if (!sessionId.value) return

  try {
    const res = await practiceApi.completeSession(sessionId.value)
    completed.value = true
    averageScore.value = res.data.average_score
    addMessage({
      id: `system-${Date.now()}`,
      role: 'system',
      content: averageScore.value != null
        ? `🎉 演练结束！本次平均评分：${averageScore.value}/5 分。`
        : '🎉 演练结束！感谢你的参与。',
      timestamp: Date.now(),
    })
    showToast('会话已完成')
  } catch (e: any) {
    showToast(e?.message || '操作失败')
  }
}

function goBack() {
  if (sending.value) {
    cancelSend()
  }
  router.back()
}

function newSession() {
  showScenePicker.value = true
  messages.value = []
  sessionId.value = 0
  completed.value = false
  averageScore.value = null
}

// ── Score color ─────────────────────────────────────────────────────
function scoreColor(score: number): string {
  if (score >= 5) return '#059669'
  if (score >= 4) return '#0e7490'
  if (score >= 3) return '#d97706'
  if (score >= 2) return '#dc2626'
  return '#991b1b'
}

function scoreStars(score: number): string {
  return '⭐'.repeat(Math.min(5, Math.max(1, Math.round(score))))
}

onMounted(() => {
  if (moduleCode.value) {
    selectScene(moduleCode.value)
  }
})
</script>

<template>
  <div class="agent-page">
    <!-- Header -->
    <van-nav-bar
      :title="sessionTitle"
      left-arrow
      fixed
      placeholder
      @click-left="goBack"
    >
      <template #right>
        <van-icon
          v-if="sessionId && !completed"
          name="add-o"
          size="20"
          @click="newSession"
          style="margin-right: 12px;"
        />
        <van-icon
          v-if="sessionId && !completed"
          name="flag-o"
          size="20"
          @click="finishSession"
        />
      </template>
    </van-nav-bar>

    <!-- Scene Picker -->
    <div v-if="showScenePicker" class="scene-picker">
      <div class="picker-header">
        <h2>选择演练场景</h2>
        <p>选择一个场景开始 AI 对话练习</p>
      </div>
      <div class="picker-grid">
        <div
          v-for="scene in sceneList"
          :key="scene.code"
          class="picker-card"
          @click="selectScene(scene.code)"
        >
          <div class="picker-icon" :style="{ background: scene.code === moduleCode ? 'var(--primary)' : '#f0f0f0' }">
            <van-icon
              :name="scene.icon"
              size="24"
              :color="scene.code === moduleCode ? '#fff' : 'var(--text-secondary)'"
            />
          </div>
          <span class="picker-name">{{ scene.title }}</span>
          <span class="picker-cat">{{ scene.category }}</span>
        </div>
      </div>
    </div>

    <!-- Chat Messages -->
    <div v-else class="chat-area">
      <van-loading v-if="loadingSession" size="24" class="chat-loading" />

      <div ref="messageListRef" class="message-list">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="msg-wrapper"
          :class="`msg-${msg.role}`"
        >
          <!-- System message -->
          <div v-if="msg.role === 'system'" class="system-msg">
            {{ msg.content }}
          </div>

          <!-- Tool call -->
          <div v-else-if="msg.role === 'tool'" class="tool-msg">
            <van-icon name="setting-o" size="14" />
            <span>{{ msg.content }}</span>
          </div>

          <!-- Evaluation card -->
          <div v-else-if="msg.role === 'evaluation' && msg.evaluation" class="eval-card">
            <div class="eval-header">
              <span class="eval-title">📊 本轮评估</span>
              <span class="eval-score" :style="{ color: scoreColor(msg.evaluation.score) }">
                {{ scoreStars(msg.evaluation.score) }} {{ msg.evaluation.score }}/{{ msg.evaluation.max_score }}
              </span>
            </div>
            <div class="eval-feedback">{{ msg.evaluation.feedback }}</div>
            <div v-if="msg.evaluation.highlights?.length" class="eval-section">
              <div class="eval-label">✅ 亮点</div>
              <ul class="eval-list">
                <li v-for="(h, i) in msg.evaluation.highlights" :key="i">{{ h }}</li>
              </ul>
            </div>
            <div v-if="msg.evaluation.improvements?.length" class="eval-section">
              <div class="eval-label">💡 改进建议</div>
              <ul class="eval-list">
                <li v-for="(imp, i) in msg.evaluation.improvements" :key="i">{{ imp }}</li>
              </ul>
            </div>
          </div>

          <!-- Chat bubble (user / assistant) -->
          <div v-else class="chat-bubble" :class="msg.role">
            <div class="bubble-avatar">
              <van-icon
                v-if="msg.role === 'assistant'"
                name="service-o"
                size="20"
                color="var(--primary)"
              />
              <van-icon
                v-else
                name="user-o"
                size="20"
                color="#fff"
              />
            </div>
            <div class="bubble-content">
              <div class="bubble-text" v-html="msg.content.replace(/\n/g, '<br>')" />
              <div v-if="msg.role === 'assistant' && !msg.content && sending" class="typing-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Bar -->
      <div class="input-bar" v-if="!showScenePicker">
        <div class="input-wrapper">
          <input
            v-model="inputText"
            class="input-field"
            :placeholder="completed ? '演练已结束' : '输入你的话术回复...'"
            :disabled="sending || completed"
            @keyup.enter="sendMessage"
          />
          <button
            v-if="!sending"
            class="send-btn"
            :class="{ active: canSend }"
            :disabled="!canSend"
            @click="sendMessage"
          >
            <van-icon name="arrow-up" size="18" color="#fff" />
          </button>
          <button v-else class="stop-btn" @click="cancelSend">
            <van-icon name="pause" size="18" color="#fff" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.agent-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

// ── Scene Picker ────────────────────────────────────────────────────
.scene-picker {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.picker-header {
  text-align: center;
  margin-bottom: 24px;

  h2 {
    font-size: 20px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 6px;
  }
  p {
    font-size: 13px;
    color: var(--text-muted);
  }
}

.picker-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  width: 100%;
  max-width: 360px;
}

.picker-card {
  background: $card;
  border-radius: $radius;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--shadow-sm);

  &:active {
    transform: scale(0.96);
    background: var(--primary-light);
  }
}

.picker-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.picker-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.picker-cat {
  font-size: 11px;
  color: var(--text-muted);
}

// ── Chat Area ───────────────────────────────────────────────────────
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-loading {
  padding: 40px 0;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 8px;
  -webkit-overflow-scrolling: touch;
}

.msg-wrapper {
  margin-bottom: 8px;
}

// System messages
.system-msg {
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
  padding: 8px 16px;
}

// Tool messages
.tool-msg {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--primary);
  background: rgba(var(--primary-rgb, 14, 116, 144), 0.08);
  padding: 4px 10px;
  border-radius: 12px;
  margin: 4px 0;
}

// Evaluation card
.eval-card {
  background: $card;
  border-radius: $radius;
  padding: 12px;
  margin: 8px 0;
  border-left: 3px solid var(--primary);
  box-shadow: var(--shadow-sm);
}

.eval-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.eval-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.eval-score {
  font-size: 14px;
  font-weight: 700;
}

.eval-feedback {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 8px;
}

.eval-section {
  margin-top: 6px;
}

.eval-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 3px;
}

.eval-list {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;

  li {
    margin-bottom: 2px;
  }
}

// Chat bubbles
.chat-bubble {
  display: flex;
  gap: 8px;
  padding: 0 4px;

  &.assistant {
    flex-direction: row;
    padding-right: 40px;

    .bubble-avatar {
      background: var(--primary-light);
    }
    .bubble-content {
      align-items: flex-start;
    }
    .bubble-text {
      background: #f0f0f0;
      color: var(--text);
      border-bottom-left-radius: 4px;
    }
  }

  &.user {
    flex-direction: row-reverse;
    padding-left: 40px;

    .bubble-avatar {
      background: var(--primary);
    }
    .bubble-content {
      align-items: flex-end;
    }
    .bubble-text {
      background: linear-gradient(135deg, var(--primary), var(--primary-dark, #065f6e));
      color: #fff;
      border-bottom-right-radius: 4px;
    }
  }
}

.bubble-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.bubble-content {
  display: flex;
  flex-direction: column;
  max-width: 100%;
  min-width: 0;
}

.bubble-text {
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.typing-dots {
  display: flex;
  gap: 4px;
  padding: 10px 14px;

  span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text-muted);
    animation: typing 1.4s infinite;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
}

// ── Input Bar ───────────────────────────────────────────────────────
.input-bar {
  padding: 8px 12px;
  padding-bottom: max(8px, env(safe-area-inset-bottom));
  background: $card;
  border-top: 1px solid var(--border);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--bg);
  border-radius: 24px;
  padding: 4px 4px 4px 16px;
  border: 1px solid var(--border);
}

.input-field {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 15px;
  line-height: 1.4;
  padding: 8px 0;
  outline: none;
  color: var(--text);
  min-height: 24px;
  max-height: 100px;
  resize: none;

  &::placeholder {
    color: var(--text-muted);
  }

  &:disabled {
    opacity: 0.5;
  }
}

.send-btn, .stop-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  cursor: pointer;
  transition: all 0.2s;

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.send-btn {
  background: var(--border);
  &.active {
    background: var(--primary);
  }
}

.stop-btn {
  background: var(--danger, #dc2626);
}
</style>
