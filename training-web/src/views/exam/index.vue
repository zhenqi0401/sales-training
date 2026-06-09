<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { examsApi } from '@/api/exams'
import type { ExamConfig } from '@/types'

const router = useRouter()

type ExamCard = ExamConfig & {
  level: 'L1' | 'L2' | 'L3'
  icon: string
  color: string
  bg: string
}

const defaultCards: ExamCard[] = [
  {
    level: 'L1',
    title: '初级考核',
    description: '基础产品知识 + 接待流程',
    questionCount: 20,
    duration: 30,
    passScore: 60,
    totalScore: 100,
    icon: 'smile-o',
    color: 'var(--success)',
    bg: 'linear-gradient(135deg, #d1fae5, #a7f3d0)'
  },
  {
    level: 'L2',
    title: '中级考核',
    description: '专业知识 + 销售技巧',
    questionCount: 30,
    duration: 45,
    passScore: 70,
    totalScore: 100,
    icon: 'star-o',
    color: 'var(--primary)',
    bg: 'linear-gradient(135deg, #cffafe, #a5f3fc)'
  },
  {
    level: 'L3',
    title: '高级考核',
    description: '综合能力 + 实战场景',
    questionCount: 40,
    duration: 60,
    passScore: 80,
    totalScore: 100,
    icon: 'award-o',
    color: 'var(--warning)',
    bg: 'linear-gradient(135deg, #fef3c7, #fde68a)'
  }
]

const exams = ref<ExamCard[]>(defaultCards)
const loading = ref(false)

const sprintMode: ExamConfig & { level: 'SPRINT'; icon: string; color: string } = {
  level: 'SPRINT',
  title: '冲刺模式',
  description: '随机抽题，限时挑战',
  questionCount: 10,
  duration: 10,
  passScore: 60,
  totalScore: 100,
  icon: 'flash-o',
  color: 'var(--danger)'
}

onMounted(loadConfigs)

async function loadConfigs() {
  loading.value = true
  try {
    const results = await Promise.all(defaultCards.map((card) => examsApi.getExamConfig(card.level)))
    exams.value = defaultCards.map((card, index) => ({
      ...card,
      ...(results[index].data || {}),
      level: card.level
    }))
  } catch {
    showToast('考试规则加载失败，已使用默认规则')
  } finally {
    loading.value = false
  }
}

async function confirmStart(config: ExamConfig, pathLevel: string) {
  await showConfirmDialog({
    title: config.title,
    message: `考试时长 ${config.duration} 分钟，共 ${config.questionCount} 题，满分 ${config.totalScore} 分，${config.passScore} 分及格。开始后会进入倒计时。`,
    confirmButtonText: '开始考试',
    cancelButtonText: '再看看'
  })
  const query = config.paperId ? `?paperId=${config.paperId}` : ''
  router.push(`/exam/taking/${pathLevel.toLowerCase()}${query}`)
}

async function startExam(exam: ExamConfig) {
  let latest = exam
  try {
    latest = (await examsApi.getExamConfig(exam.level)).data || exam
  } catch {
    showToast('考试规则加载失败，请稍后重试')
    return
  }

  try {
    await confirmStart(latest, latest.level)
  } catch {
    // User cancelled.
  }
}

async function startSprint() {
  try {
    await confirmStart(sprintMode, sprintMode.level)
  } catch {
    // User cancelled.
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">在线考试</h2>
      <p class="page-subtitle">选择试卷、确认规则后进入倒计时答题</p>
    </div>

    <van-loading v-if="loading" size="22" class="inline-loading" />

    <div class="exam-section">
      <h3 class="section-title">等级考核</h3>

      <div v-for="exam in exams" :key="exam.level" class="exam-card" @click="startExam(exam)">
        <div class="exam-card-bg" :style="{ background: exam.bg }">
          <van-icon :name="exam.icon" size="34" :color="exam.color" />
        </div>
        <div class="exam-card-info">
          <div class="exam-title">{{ exam.title }}</div>
          <div class="exam-desc">{{ exam.description }}</div>
          <div class="exam-meta">
            <span>{{ exam.questionCount }}题</span>
            <span class="meta-dot">|</span>
            <span>{{ exam.duration }}分钟</span>
            <span class="meta-dot">|</span>
            <span>{{ exam.passScore }}分及格</span>
          </div>
        </div>
        <van-icon name="arrow" size="18" color="var(--text-muted)" />
      </div>
    </div>

    <div class="exam-section">
      <h3 class="section-title">快速挑战</h3>

      <div class="sprint-card" @click="startSprint">
        <div class="sprint-icon">
          <van-icon :name="sprintMode.icon" size="42" :color="sprintMode.color" />
        </div>
        <div class="sprint-info">
          <div class="sprint-title">{{ sprintMode.title }}</div>
          <div class="sprint-desc">{{ sprintMode.description }}</div>
          <div class="sprint-meta">{{ sprintMode.questionCount }}题 | {{ sprintMode.duration }}分钟快答</div>
        </div>
        <van-button round size="small" color="var(--danger)">开始</van-button>
      </div>
    </div>

    <div class="section-card action-entry" @click="router.push('/exam/wrong-book')">
      <van-icon name="notes-o" size="30" color="var(--primary)" />
      <div class="wrong-book-info">
        <div class="wrong-book-title">错题本</div>
        <div class="wrong-book-desc">按分类和知识点复盘，可直接重练错题</div>
      </div>
      <van-icon name="arrow" size="16" color="var(--text-muted)" />
    </div>

    <div class="section-card action-entry" @click="router.push('/profile/records')">
      <van-icon name="chart-trending-o" size="30" color="var(--success)" />
      <div class="wrong-book-info">
        <div class="wrong-book-title">成绩记录</div>
        <div class="wrong-book-desc">查看历次成绩和趋势变化</div>
      </div>
      <van-icon name="arrow" size="16" color="var(--text-muted)" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-header {
  padding: 16px 16px 8px;
  background: $card;
  margin-bottom: 4px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}

.inline-loading {
  padding: 14px 0 2px;
}

.exam-section {
  padding: 12px 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}

.exam-card,
.sprint-card,
.action-entry {
  display: flex;
  align-items: center;
  gap: 14px;
  background: $card;
  border-radius: $radius;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: transform 0.2s, opacity 0.2s;

  &:active {
    transform: translateX(4px);
    opacity: 0.86;
  }
}

.exam-card-bg,
.sprint-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.exam-card-bg {
  border-radius: 12px;
}

.exam-card-info,
.sprint-info,
.wrong-book-info {
  flex: 1;
  min-width: 0;
}

.exam-title,
.sprint-title,
.wrong-book-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.exam-desc,
.sprint-desc,
.wrong-book-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.exam-meta,
.sprint-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
}

.meta-dot {
  color: var(--border);
}
</style>
