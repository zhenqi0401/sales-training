<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { examsApi } from '@/api/exams'
import QuestionCard from '@/components/exam/QuestionCard.vue'
import type { Question } from '@/types'

const route = useRoute()
const router = useRouter()

const level = computed(() => (route.params.level as string).toUpperCase())
const loading = ref(true)
const submitting = ref(false)

const questions = ref<Question[]>([])
const answers = ref<Record<number, string | string[]>>({})
const markedQuestions = ref<number[]>([])
const currentIndex = ref(0)
const timeLeft = ref(0) // seconds
const totalTime = ref(0)

let timer: ReturnType<typeof setInterval> | null = null

const currentQuestion = computed(() => questions.value[currentIndex.value] || null)

const progress = computed(() => {
  if (questions.value.length === 0) return 0
  return Math.round((Object.keys(answers.value).length / questions.value.length) * 100)
})

const answeredCount = computed(() => Object.keys(answers.value).length)

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

onMounted(async () => {
  try {
    let data: Question[]
    if (level.value === 'SPRINT') {
      const res = await examsApi.getSprintQuestions()
      data = res.data || []
      totalTime.value = 600 // 10 min
    } else {
      const res = await examsApi.getQuestions(level.value)
      data = res.data || []
      totalTime.value = level.value === 'L1' ? 1800 : level.value === 'L2' ? 2700 : 3600
    }
    questions.value = data
    timeLeft.value = totalTime.value

    // Start countdown
    timer = setInterval(() => {
      timeLeft.value--
      if (timeLeft.value <= 0) {
        handleSubmit()
      }
    }, 1000)
  } catch {
    showToast('加载失败')
    router.back()
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})

function onSelect(value: string | string[]) {
  if (currentQuestion.value) {
    answers.value[currentQuestion.value.id] = value
  }
}

function toggleMark() {
  if (currentQuestion.value) {
    const id = currentQuestion.value.id
    const idx = markedQuestions.value.indexOf(id)
    if (idx !== -1) {
      markedQuestions.value.splice(idx, 1)
    } else {
      markedQuestions.value.push(id)
    }
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

async function handleSubmit() {
  const unanswered = questions.value.length - answeredCount.value
  if (unanswered > 0) {
    try {
      await showConfirmDialog({
        title: '提交确认',
        message: `还有 ${unanswered} 题未作答，确定提交吗？`,
        confirmButtonText: '确定提交',
        cancelButtonText: '继续答题'
      })
    } catch {
      return // User cancelled
    }
  } else {
    try {
      await showConfirmDialog({
        title: '提交确认',
        message: '确定要提交试卷吗？',
        confirmButtonText: '确定提交'
      })
    } catch {
      return
    }
  }

  submitting.value = true
  if (timer) {
    clearInterval(timer)
    timer = null
  }

  try {
    const duration = totalTime.value - timeLeft.value
    const res = await examsApi.submitExam({
      level: level.value,
      answers: Object.entries(answers.value).map(([questionId, selected]) => ({
        questionId: Number(questionId),
        selected
      })),
      duration
    })
    showToast('提交成功')
    router.replace(`/exam/result/${res.data.id}`)
  } catch {
    showToast('提交失败，请重试')
    submitting.value = false
  }
}
</script>

<template>
  <div class="exam-taking-page page-no-tabbar">
    <!-- Header with timer -->
    <div class="exam-header">
      <div class="header-left" @click="handleSubmit">
        <van-icon name="cross" size="20" />
        <span class="exit-text">退出</span>
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

    <!-- Question progress info -->
    <div class="exam-progress-info">
      <span class="answered">{{ answeredCount }}/{{ questions.length }} 已答</span>
      <span class="marked-count" v-if="markedQuestions.length > 0">
        <van-icon name="flag-o" size="12" color="var(--warning)" />
        {{ markedQuestions.length }} 标记
      </span>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading" />

    <!-- Question Card -->
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

      <!-- Bottom actions -->
      <div class="bottom-actions">
        <div class="action-left">
          <van-button
            round
            plain
            type="default"
            size="small"
            icon="arrow-left"
            :disabled="currentIndex === 0"
            @click="prevQuestion"
          >
            上一题
          </van-button>
          <van-button
            round
            plain
            type="default"
            size="small"
            :icon="currentIndex === questions.length - 1 ? '' : 'arrow'"
            :class="{ 'is-last': currentIndex === questions.length - 1 }"
            @click="nextQuestion"
          >
            {{ currentIndex === questions.length - 1 ? '最后一题' : '下一题' }}
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
            @click="handleSubmit"
            :loading="submitting"
          >
            交卷
          </van-button>
        </div>
      </div>

      <!-- Question Navigator -->
      <div class="question-navigator" v-if="questions.length > 0">
        <div
          v-for="(q, idx) in questions"
          :key="q.id"
          class="nav-dot"
          :class="{
            answered: answers[q.id],
            current: idx === currentIndex,
            marked: markedQuestions.includes(q.id)
          }"
          @click="goQuestion(idx)"
        >
          {{ idx + 1 }}
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

.header-center {
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;

  &.urgent {
    color: var(--danger);
  }
}

.header-left {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  font-size: 14px;
}

.exam-progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 20px;
  font-size: 12px;
  color: var(--text-muted);
  background: $card;
  border-bottom: 1px solid var(--border-light);
}

.marked-count {
  display: flex;
  align-items: center;
  gap: 4px;
}

.question-area {
  padding: 12px 0;
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

.question-navigator {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 12px 16px;
  margin: 12px 16px;
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

  &:active {
    transform: scale(0.9);
  }
}
</style>
