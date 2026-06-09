<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { examsApi } from '@/api/exams'
import QuestionCard from '@/components/exam/QuestionCard.vue'
import type { ExamConfig, Question } from '@/types'

const route = useRoute()
const router = useRouter()

const level = computed(() => (route.params.level as string).toUpperCase())
const loading = ref(true)
const submitting = ref(false)
const autoSubmitting = ref(false)

const config = ref<ExamConfig | null>(null)
const questions = ref<Question[]>([])
const answers = ref<Record<number, string | string[]>>({})
const markedQuestions = ref<number[]>([])
const currentIndex = ref(0)
const timeLeft = ref(0)
const totalTime = ref(0)

let timer: ReturnType<typeof setInterval> | null = null

const currentQuestion = computed(() => questions.value[currentIndex.value] || null)
const answeredCount = computed(() => Object.keys(answers.value).filter((id) => hasAnswer(answers.value[Number(id)])).length)
const progress = computed(() => {
  if (questions.value.length === 0) return 0
  return Math.round((answeredCount.value / questions.value.length) * 100)
})

onMounted(loadExam)
onUnmounted(stopTimer)

async function loadExam() {
  loading.value = true
  try {
    const configRes = await examsApi.getExamConfig(level.value)
    config.value = configRes.data
    totalTime.value = Math.max((config.value?.duration || 30) * 60, 60)

    const questionRes = level.value === 'SPRINT'
      ? await examsApi.getSprintQuestions()
      : await examsApi.getQuestions(level.value)

    questions.value = questionRes.data || []
    if (questions.value.length === 0) {
      showToast(level.value === 'WRONG' ? '暂无错题可练习' : '暂无可用题目')
      router.replace('/exam')
      return
    }

    timeLeft.value = totalTime.value
    startTimer()
  } catch {
    showToast('加载考试失败')
    router.replace('/exam')
  } finally {
    loading.value = false
  }
}

function startTimer() {
  stopTimer()
  timer = setInterval(() => {
    timeLeft.value = Math.max(timeLeft.value - 1, 0)
    if (timeLeft.value === 0) {
      autoSubmitting.value = true
      handleSubmit(true)
    }
  }, 1000)
}

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function hasAnswer(value: string | string[] | undefined) {
  if (Array.isArray(value)) return value.length > 0
  return !!value
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function onSelect(value: string | string[]) {
  if (currentQuestion.value) {
    answers.value[currentQuestion.value.id] = value
  }
}

function toggleMark() {
  if (!currentQuestion.value) return
  const id = currentQuestion.value.id
  const index = markedQuestions.value.indexOf(id)
  if (index >= 0) {
    markedQuestions.value.splice(index, 1)
  } else {
    markedQuestions.value.push(id)
  }
}

function goQuestion(index: number) {
  currentIndex.value = index
}

function prevQuestion() {
  if (currentIndex.value > 0) currentIndex.value--
}

function nextQuestion() {
  if (currentIndex.value < questions.value.length - 1) currentIndex.value++
}

async function confirmSubmit(unanswered: number) {
  if (autoSubmitting.value) return
  await showConfirmDialog({
    title: '提交确认',
    message: unanswered > 0
      ? `还有 ${unanswered} 题未作答，确定提交吗？`
      : '确定提交试卷吗？',
    confirmButtonText: '确定提交',
    cancelButtonText: unanswered > 0 ? '继续答题' : '再检查'
  })
}

async function handleSubmit(force = false) {
  if (submitting.value || questions.value.length === 0) return

  const unanswered = questions.value.length - answeredCount.value
  if (!force) {
    try {
      await confirmSubmit(unanswered)
    } catch {
      return
    }
  }

  submitting.value = true
  stopTimer()

  try {
    const paperId = Number(route.query.paperId || config.value?.paperId || 0) || undefined
    const duration = Math.max(totalTime.value - timeLeft.value, 0)
    const res = await examsApi.submitExam({
      level: level.value,
      paperId,
      answers: questions.value.map((question) => ({
        questionId: question.id,
        selected: answers.value[question.id] || (question.type === 'multi' ? [] : '')
      })),
      duration
    })
    showToast(force ? '时间到，已自动交卷' : '提交成功')
    router.replace(`/exam/result/${res.data.id}`)
  } catch {
    showToast('提交失败，请重试')
    submitting.value = false
    autoSubmitting.value = false
    startTimer()
  }
}
</script>

<template>
  <div class="exam-taking-page page-no-tabbar">
    <div class="exam-header">
      <div class="header-left" @click="handleSubmit(false)">
        <van-icon name="cross" size="20" />
        <span class="exit-text">交卷</span>
      </div>
      <div class="header-center">
        <van-progress
          :percentage="progress"
          :stroke-width="4"
          color="linear-gradient(90deg, var(--primary), var(--success))"
          track-color="#e2e8f0"
          :show-pivot="false"
        />
      </div>
      <div class="header-right" :class="{ urgent: timeLeft < 300 }">
        <van-icon name="clock-o" size="14" />
        <span>{{ formatTime(timeLeft) }}</span>
      </div>
    </div>

    <div class="exam-progress-info">
      <span class="answered">{{ answeredCount }}/{{ questions.length }} 已答</span>
      <span class="paper-title">{{ config?.title || '考试' }}</span>
      <span class="marked-count" v-if="markedQuestions.length > 0">
        <van-icon name="flag-o" size="12" color="var(--warning)" />
        {{ markedQuestions.length }} 标记
      </span>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else-if="currentQuestion">
      <div class="question-area">
        <QuestionCard
          :key="currentQuestion.id"
          :question="currentQuestion"
          :index="currentIndex"
          :selected="answers[currentQuestion.id] || (currentQuestion.type === 'multi' ? [] : '')"
          @select="onSelect"
        />
      </div>

      <div class="question-navigator">
        <div
          v-for="(question, idx) in questions"
          :key="question.id"
          class="nav-dot"
          :class="{
            answered: hasAnswer(answers[question.id]),
            current: idx === currentIndex,
            marked: markedQuestions.includes(question.id)
          }"
          @click="goQuestion(idx)"
        >
          {{ idx + 1 }}
        </div>
      </div>

      <div class="bottom-actions">
        <div class="action-left">
          <van-button round plain type="default" size="small" icon="arrow-left" :disabled="currentIndex === 0" @click="prevQuestion">
            上一题
          </van-button>
          <van-button round plain type="default" size="small" :disabled="currentIndex === questions.length - 1" icon="arrow" @click="nextQuestion">
            下一题
          </van-button>
        </div>
        <div class="action-right">
          <van-button
            round
            plain
            size="small"
            :icon="currentQuestion && markedQuestions.includes(currentQuestion.id) ? 'flag' : 'flag-o'"
            :color="currentQuestion && markedQuestions.includes(currentQuestion.id) ? 'var(--warning)' : 'var(--text-muted)'"
            @click="toggleMark"
          >
            {{ currentQuestion && markedQuestions.includes(currentQuestion.id) ? '已标记' : '标记' }}
          </van-button>
          <van-button
            round
            type="primary"
            size="small"
            color="linear-gradient(135deg, var(--primary), var(--primary-dark))"
            :loading="submitting"
            @click="handleSubmit(false)"
          >
            提交
          </van-button>
        </div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.exam-taking-page {
  min-height: 100vh;
  background: $bg;
  padding-bottom: 120px;
}

.page-loading {
  padding: 60px 0;
}

.exam-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: $card;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--text-secondary);
}

.header-center {
  flex: 1;
}

.header-right {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;

  &.urgent {
    color: var(--danger);
  }
}

.exam-progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  font-size: 12px;
  color: var(--text-muted);
  background: $card;
  border-bottom: 1px solid var(--border-light);
}

.paper-title {
  flex: 1;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.marked-count {
  display: flex;
  align-items: center;
  gap: 4px;
}

.question-area {
  padding: 12px 0;
}

.question-navigator {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 12px 16px;
  margin: 0 16px 12px;
  background: $card;
  border-radius: $radius;
}

.nav-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
  background: #f1f5f9;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;

  &.answered {
    background: rgba(14, 116, 144, 0.15);
    color: var(--primary);
    font-weight: 700;
  }

  &.current {
    border: 2px solid var(--primary);
    font-weight: 700;
  }

  &.marked {
    border: 2px solid var(--warning);
    color: var(--warning);
  }
}

.bottom-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: $card;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 10;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}

.action-left,
.action-right {
  display: flex;
  gap: 8px;
}
</style>
