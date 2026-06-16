<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { learningApi } from '@/api/learning'
import { useLearningStore } from '@/stores/learning'
import type { Video } from '@/types'
import { showToast } from 'vant'
import QuestionCard from '@/components/exam/QuestionCard.vue'

const route = useRoute()
const router = useRouter()
const learningStore = useLearningStore()
const videoId = computed(() => Number(route.params.videoId))

const video = ref<Video | null>(null)
const videoRef = ref<HTMLVideoElement | null>(null)
const loading = ref(true)
const playing = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const progress = ref(0)
const videoOrientation = ref<'landscape' | 'portrait' | 'square'>('landscape')

// ── Quiz / practice state ──
const quizShow = ref(false)
const quizLoading = ref(false)
const quizQuestions = ref<any[]>([])
const quizVideoTitle = ref('')
const quizCurrentIndex = ref(0)
const quizAnswers = ref<Record<number, string | string[]>>({})
const quizChecked = ref<Record<number, { correct: boolean; correctAnswer: string; analysis: string }>>({})
const quizSubmitted = ref(false)

let progressTimer: ReturnType<typeof setInterval> | null = null
let progressSaving = false
let pendingProgressSave = false
let lastSyncedProgress: {
  videoId: number
  watchDuration: number
  progress: number
  completed: boolean
} | null = null

onMounted(async () => {
  try {
    const res = await learningApi.getVideoDetail(videoId.value)
    video.value = res.data
    duration.value = video.value.duration
    updateVideoOrientationFromResolution(video.value.resolution)

    const saved = learningStore.videoProgress[videoId.value]
    if (saved) {
      progress.value = saved.progress
      if (videoRef.value && saved.watchDuration > 0) {
        videoRef.value.currentTime = saved.watchDuration
      }
    }
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  stopProgressTimer()
  void saveProgress({ force: true })
  if (videoRef.value) {
    videoRef.value.pause()
  }
})

function startProgressTimer() {
  stopProgressTimer()
  progressTimer = setInterval(() => {
    if (!video.value) return
    const ct = videoRef.value?.currentTime ?? currentTime.value
    currentTime.value = Math.floor(ct)
    if (duration.value > 0) {
      progress.value = Math.min(100, Math.round((currentTime.value / duration.value) * 100))
    }
    void saveProgress()
  }, 1000)
}

function stopProgressTimer() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

function onVideoPlay() {
  playing.value = true
  startProgressTimer()
}

function onVideoPause() {
  playing.value = false
  stopProgressTimer()
  void saveProgress({ force: true })
}

function onVideoEnded() {
  playing.value = false
  stopProgressTimer()
  completeVideo()
}

function onVideoTimeUpdate() {
  if (!videoRef.value) return
  currentTime.value = Math.floor(videoRef.value.currentTime)
}

function onVideoLoadedMetadata() {
  if (!videoRef.value) return
  duration.value = Math.floor(videoRef.value.duration)
  updateVideoOrientation(videoRef.value.videoWidth, videoRef.value.videoHeight)
  const saved = learningStore.videoProgress[videoId.value]
  if (saved?.watchDuration) {
    videoRef.value.currentTime = saved.watchDuration
  }
}

function updateVideoOrientationFromResolution(resolution?: string) {
  const match = /^(\d+)x(\d+)$/i.exec(resolution || '')
  if (!match) return
  updateVideoOrientation(Number(match[1]), Number(match[2]))
}

function updateVideoOrientation(width: number, height: number) {
  if (!width || !height) return
  if (Math.abs(width - height) <= 2) {
    videoOrientation.value = 'square'
  } else {
    videoOrientation.value = width > height ? 'landscape' : 'portrait'
  }
}

function shouldSyncProgress(completed: boolean) {
  if (!video.value) return false
  if (!lastSyncedProgress) return true
  if (lastSyncedProgress.videoId !== video.value.id) return true
  if (completed && !lastSyncedProgress.completed) return true
  return currentTime.value - lastSyncedProgress.watchDuration >= 5
}

async function saveProgress(options: { force?: boolean } = {}) {
  if (!video.value) return
  const completed = progress.value >= 90
  learningStore.updateVideoProgress(video.value.id, {
    progress: progress.value,
    completed,
    watchDuration: currentTime.value,
  })
  if (!options.force && !shouldSyncProgress(completed)) return
  if (progressSaving) {
    pendingProgressSave = true
    return
  }

  const payload = {
    videoId: video.value.id,
    watchDuration: currentTime.value,
    progress: progress.value,
    completed,
  }

  progressSaving = true
  try {
    await learningApi.updateProgress(payload)
    lastSyncedProgress = payload
  } catch {
    // Local progress is available and will be overwritten after the next successful sync.
  } finally {
    progressSaving = false
    if (pendingProgressSave) {
      pendingProgressSave = false
      void saveProgress({ force: true })
    }
  }
}

async function completeVideo() {
  if (!video.value) return
  playing.value = false
  progress.value = 100
  learningStore.updateVideoProgress(video.value.id, {
    progress: 100,
    completed: true,
    watchDuration: duration.value,
  })
  try {
    await learningApi.updateProgress({
      videoId: video.value.id,
      progress: 100,
      completed: true,
      watchDuration: duration.value,
    })
    lastSyncedProgress = {
      videoId: video.value.id,
      progress: 100,
      completed: true,
      watchDuration: duration.value,
    }
  } catch {
    // Keep the completion state locally if the network is temporarily unavailable.
  }
  showToast('学习完成！')
  // Try to load practice questions
  loadQuiz()
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

// ── Quiz functions ──

async function loadQuiz() {
  if (!video.value) return
  quizLoading.value = true
  try {
    const res = await learningApi.getVideoQuestions(video.value.id)
    const data = (res as any).data
    if (data && data.questions && data.questions.length > 0) {
      quizVideoTitle.value = data.videoTitle || video.value.title
      // Transform options from {A: text, B: text} to [{label, value, content}]
      quizQuestions.value = data.questions.map((q: any) => ({
        ...q,
        type: mapQuestionType(q.type),
        score: 0,
        options: transformOptions(q.options),
      }))
      quizCurrentIndex.value = 0
      quizAnswers.value = {}
      quizChecked.value = {}
      quizSubmitted.value = false
      quizShow.value = true
    }
  } catch {
    // No questions or error — silently skip
  } finally {
    quizLoading.value = false
  }
}

function transformOptions(options: any): Array<{ label: string; value: string; content: string }> {
  if (!options) return []
  if (Array.isArray(options)) return options
  // {A: "text", B: "text"} → [{label: "A", value: "A", content: "text"}]
  return Object.entries(options).map(([label, content]) => ({
    label,
    value: label,
    content: String(content),
  }))
}

function mapQuestionType(type: string): string {
  // Map backend types to QuestionCard types
  const map: Record<string, string> = { single: 'single', multiple: 'multi', true_false: 'judge' }
  return map[type] || 'single'
}

function quizCurrentQuestion(): any {
  return quizQuestions.value[quizCurrentIndex.value] || null
}

function quizCurrentSelected(): string | string[] {
  const q = quizCurrentQuestion()
  if (!q) return ''
  return quizAnswers.value[q.id] ?? ''
}

function onQuizSelect(val: string | string[]) {
  const q = quizCurrentQuestion()
  if (!q) return
  quizAnswers.value[q.id] = val
}

async function submitQuizAnswer() {
  const q = quizCurrentQuestion()
  if (!q) return
  const selected = quizAnswers.value[q.id]
  if (!selected || (Array.isArray(selected) && selected.length === 0)) {
    showToast('请先选择答案')
    return
  }
  if (quizChecked.value[q.id] !== undefined) return // already checked

  try {
    const res = await learningApi.checkVideoAnswers(video.value!.id, [
      { questionId: q.id, selected },
    ])
    const data = (res as any).data
    if (data && data.results && data.results.length > 0) {
      quizChecked.value[q.id] = data.results[0]
    }
  } catch {
    showToast('提交失败，请重试')
  }
}

function nextQuizQuestion() {
  if (quizCurrentIndex.value < quizQuestions.value.length - 1) {
    quizCurrentIndex.value++
  } else {
    quizSubmitted.value = true
  }
}

function quizCorrectCount(): number {
  return Object.values(quizChecked.value).filter((r: any) => r.correct).length
}

function closeQuiz() {
  quizShow.value = false
  quizQuestions.value = []
  quizAnswers.value = {}
  quizChecked.value = {}
  quizSubmitted.value = false
}
</script>

<template>
  <div class="play-page page-no-tabbar">
    <van-nav-bar
      title="视频学习"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else-if="video">
      <!-- Video Player -->
      <div class="player-area" :class="`is-${videoOrientation}`">
        <video
          ref="videoRef"
          class="video-element"
          :src="video.url"
          :poster="video.cover"
          playsinline
          controls
          @play="onVideoPlay"
          @pause="onVideoPause"
          @ended="onVideoEnded"
          @timeupdate="onVideoTimeUpdate"
          @loadedmetadata="onVideoLoadedMetadata"
        />
      </div>

      <!-- Progress Bar -->
      <div class="progress-section">
        <div class="progress-row">
          <span class="time-label">{{ formatTime(currentTime) }}</span>
          <van-progress
            :percentage="progress"
            :stroke-width="6"
            color="linear-gradient(90deg, var(--primary), var(--success))"
            track-color="#e2e8f0"
            :show-pivot="false"
          />
          <span class="time-label">{{ formatTime(duration) }}</span>
        </div>
      </div>

      <!-- Video Info -->
      <div class="video-info section-card">
        <h3 class="video-title">{{ video.title }}</h3>
        <div class="video-meta">
          <span class="meta-item">
            <van-icon name="manager-o" size="14" />
            {{ video.讲师 || '讲师' }}
          </span>
          <span class="meta-item">
            <van-icon name="clock-o" size="14" />
            {{ formatTime(video.duration) }}
          </span>
          <span class="meta-item" :class="{ completed: video.completed }">
            <van-icon :name="video.completed ? 'checked' : 'underway-o'" size="14" />
            {{ video.completed ? '已完成' : '学习中' }}
          </span>
        </div>
        <div class="video-desc" v-if="video.description">
          <p>{{ video.description }}</p>
        </div>
      </div>
    </template>

    <!-- Quiz Popup -->
    <van-popup v-model:show="quizShow" position="bottom" round :style="{ height: '90vh' }" teleport="body">
      <div class="quiz-container">
        <div class="quiz-header">
          <van-icon name="cross" size="20" @click="closeQuiz" />
          <span class="quiz-title">课后练习</span>
          <span class="quiz-progress">{{ quizCurrentIndex + 1 }}/{{ quizQuestions.length }}</span>
        </div>
        <div class="quiz-video-title">{{ quizVideoTitle }}</div>

        <div class="quiz-body" v-if="!quizSubmitted">
          <QuestionCard
            v-if="quizCurrentQuestion()"
            :question="quizCurrentQuestion()"
            :index="quizCurrentIndex"
            :selected="quizCurrentSelected()"
            @select="onQuizSelect"
          />

          <!-- Feedback after check -->
          <div v-if="quizChecked[quizCurrentQuestion()?.id]" class="quiz-feedback">
            <div class="feedback-result" :class="quizChecked[quizCurrentQuestion()?.id].correct ? 'correct' : 'wrong'">
              <van-icon :name="quizChecked[quizCurrentQuestion()?.id].correct ? 'success' : 'cross'" />
              {{ quizChecked[quizCurrentQuestion()?.id].correct ? '回答正确！' : '回答错误' }}
            </div>
            <div class="feedback-answer" v-if="!quizChecked[quizCurrentQuestion()?.id].correct">
              正确答案：{{ quizChecked[quizCurrentQuestion()?.id].correctAnswer }}
            </div>
            <div class="feedback-analysis" v-if="quizChecked[quizCurrentQuestion()?.id].analysis">
              {{ quizChecked[quizCurrentQuestion()?.id].analysis }}
            </div>
          </div>
        </div>

        <!-- Quiz summary -->
        <div class="quiz-body" v-else>
          <div class="quiz-summary">
            <van-icon name="checked" size="48" color="var(--success)" />
            <h3>练习完成！</h3>
            <p class="quiz-score">正确率 {{ quizCorrectCount() }} / {{ quizQuestions.length }}</p>
            <van-button type="primary" round block @click="closeQuiz">关闭</van-button>
          </div>
        </div>

        <div class="quiz-footer" v-if="!quizSubmitted">
          <van-button
            v-if="quizChecked[quizCurrentQuestion()?.id] === undefined"
            type="primary"
            round
            block
            @click="submitQuizAnswer"
          >
            提交
          </van-button>
          <van-button
            v-else
            type="primary"
            round
            block
            @click="nextQuizQuestion"
          >
            {{ quizCurrentIndex < quizQuestions.length - 1 ? '下一题' : '查看结果' }}
          </van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style lang="scss" scoped>
.page-loading {
  padding: 60px 0;
}

.player-area {
  position: relative;
  width: 100%;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  aspect-ratio: 16 / 9;
}

.player-area.is-portrait {
  aspect-ratio: 9 / 16;
  max-height: calc(100vh - 46px);
}

.player-area.is-square {
  aspect-ratio: 1 / 1;
}

.video-element {
  width: 100%;
  height: 100%;
  display: block;
  background: #000;
  object-fit: contain;
}

.progress-section {
  padding: 12px 16px;
  background: $card;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-label {
  font-size: 12px;
  color: var(--text-muted);
  min-width: 36px;
  text-align: center;
}

.video-info {
  margin-top: 0;
}

.video-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}

.video-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-secondary);

  &.completed {
    color: var(--success);
  }
}

.video-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.7;
}

// ── Quiz popup ──
.quiz-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.quiz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.quiz-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
}

.quiz-progress {
  font-size: 14px;
  color: var(--text-muted);
}

.quiz-video-title {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 8px 16px;
  background: var(--bg-secondary, #f5f7fa);
  flex-shrink: 0;
}

.quiz-body {
  flex: 1;
  overflow-y: auto;
  padding-top: 12px;
}

.quiz-feedback {
  margin: 0 16px 12px;
  padding: 12px 16px;
  background: $card;
  border-radius: $radius;
}

.feedback-result {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;

  &.correct {
    color: var(--success);
  }
  &.wrong {
    color: var(--danger, #e74c3c);
  }
}

.feedback-answer {
  font-size: 14px;
  color: var(--primary);
  margin-bottom: 6px;
}

.feedback-analysis {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}

.quiz-summary {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  text-align: center;

  h3 {
    margin: 16px 0 8px;
    font-size: 20px;
    color: var(--text);
  }
}

.quiz-score {
  font-size: 18px;
  color: var(--primary);
  font-weight: 600;
  margin-bottom: 24px;
}

.quiz-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
</style>
