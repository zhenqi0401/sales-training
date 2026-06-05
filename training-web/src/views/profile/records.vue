<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { learningApi } from '@/api/learning'
import { examsApi } from '@/api/exams'
import type { ExamRecord } from '@/types'
import { showToast } from 'vant'

const router = useRouter()
const loading = ref(true)
const activeTab = ref(0)

// Learning stats
const learningStats = ref({
  totalVideos: 0,
  completedVideos: 0,
  totalDuration: 0,
  todayDuration: 0,
  streakDays: 0
})

// Exam history
const examRecords = ref<ExamRecord[]>([])

onMounted(async () => {
  try {
    const [statsRes, examRes] = await Promise.all([
      learningApi.getLearningStats(),
      examsApi.getExamHistory()
    ])
    learningStats.value = statsRes.data || { totalVideos: 0, completedVideos: 0, totalDuration: 0, todayDuration: 0, streakDays: 0 }
    examRecords.value = examRes.data?.items || []
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}秒`
  const m = Math.floor(seconds / 60)
  if (m < 60) return `${m}分钟`
  const h = Math.floor(m / 60)
  const r = m % 60
  return `${h}小时${r > 0 ? `${r}分钟` : ''}`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function goExamResult(recordId: number) {
  router.push(`/exam/result/${recordId}`)
}

const levelLabels: Record<string, string> = {
  L1: '初级',
  L2: '中级',
  L3: '高级',
  SPRINT: '冲刺'
}
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar
      title="学习记录"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else>
      <!-- Stats Overview -->
      <div class="stats-overview">
        <div class="stat-block">
          <span class="stat-value">{{ learningStats.streakDays }}</span>
          <span class="stat-label">连续天数</span>
        </div>
        <div class="stat-block">
          <span class="stat-value">{{ learningStats.completedVideos }}</span>
          <span class="stat-label">完成课程</span>
        </div>
        <div class="stat-block">
          <span class="stat-value">{{ formatDuration(learningStats.totalDuration) }}</span>
          <span class="stat-label">总学习时长</span>
        </div>
        <div class="stat-block">
          <span class="stat-value">{{ formatDuration(learningStats.todayDuration) }}</span>
          <span class="stat-label">今日学习</span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="section-card">
        <van-tabs v-model:active="activeTab" color="var(--primary)" title-active-color="var(--primary)">
          <van-tab title="课程进度">
            <div class="tab-content">
              <div class="progress-summary">
                <div class="progress-row">
                  <span class="progress-text">学习进度</span>
                  <span class="progress-value">{{ learningStats.completedVideos }}/{{ learningStats.totalVideos }}</span>
                </div>
                <van-progress
                  :percentage="learningStats.totalVideos > 0 ? Math.round((learningStats.completedVideos / learningStats.totalVideos) * 100) : 0"
                  :stroke-width="8"
                  color="linear-gradient(90deg, var(--primary), var(--success))"
                  track-color="#e2e8f0"
                  :show-pivot="false"
                />
              </div>
            </div>
          </van-tab>

          <van-tab title="考试记录">
            <div class="tab-content">
              <div v-if="examRecords.length === 0" class="empty-tab">
                <span class="text-muted">暂无考试记录</span>
              </div>
              <div
                v-for="record in examRecords"
                :key="record.id"
                class="exam-record-item"
                @click="goExamResult(record.id)"
              >
                <div class="record-left">
                  <div class="record-level" :class="record.passed ? 'pass' : 'fail'">
                    {{ levelLabels[record.examLevel] || record.examLevel }}
                  </div>
                  <div class="record-info">
                    <span class="record-score">{{ record.score }}分</span>
                    <span class="record-date">{{ formatDate(record.submittedAt) }}</span>
                  </div>
                </div>
                <div class="record-right">
                  <van-tag
                    round
                    :color="record.passed ? 'var(--success)' : 'var(--danger)'"
                    size="small"
                  >
                    {{ record.passed ? '通过' : '未通过' }}
                  </van-tag>
                  <van-icon name="arrow" size="14" color="var(--text-muted)" />
                </div>
              </div>
            </div>
          </van-tab>
        </van-tabs>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page-loading {
  padding: 60px 0;
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 16px;
  background: $card;
}

.stat-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
}

.tab-content {
  padding: 16px 0;
  min-height: 100px;
}

.progress-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.progress-text {
  color: var(--text-secondary);
}

.progress-value {
  font-weight: 600;
  color: var(--text);
}

.empty-tab {
  text-align: center;
  padding: 24px 0;
}

.exam-record-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;

  &:last-child {
    border-bottom: none;
  }

  &:active {
    opacity: 0.7;
  }
}

.record-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.record-level {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;

  &.pass {
    background: var(--success-light);
    color: var(--success);
  }

  &.fail {
    background: #fecaca;
    color: var(--danger);
  }
}

.record-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.record-score {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.record-date {
  font-size: 12px;
  color: var(--text-muted);
}

.record-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
