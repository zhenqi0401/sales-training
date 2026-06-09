<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { learningApi } from '@/api/learning'
import { examsApi } from '@/api/exams'
import CalendarHeatmap from '@/components/course/CalendarHeatmap.vue'
import type { CalendarDay, ExamRecord } from '@/types'

const router = useRouter()
const loading = ref(true)
const activeTab = ref(0)
const calendarLoading = ref(false)

const learningStats = ref({
  totalVideos: 0,
  completedVideos: 0,
  totalDuration: 0,
  todayDuration: 0,
  streakDays: 0
})
const calendarData = ref<CalendarDay[]>([])
const examRecords = ref<ExamRecord[]>([])
const trendData = ref<Array<{ recordId: number; score: number; passed: boolean; submittedAt: string }>>([])

const trendMaxScore = computed(() => Math.max(100, ...trendData.value.map((item) => item.score)))

const levelLabels: Record<string, string> = {
  L1: '初级',
  L2: '中级',
  L3: '高级',
  SPRINT: '冲刺',
  WRONG: '错题'
}

onMounted(async () => {
  try {
    const [statsRes, examRes, trendRes] = await Promise.all([
      learningApi.getLearningStats(),
      examsApi.getExamHistory(),
      examsApi.getTrend()
    ])
    learningStats.value = statsRes.data || learningStats.value
    examRecords.value = examRes.data?.items || []
    trendData.value = trendRes.data || []
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }

  loadCalendar()
})

async function loadCalendar() {
  calendarLoading.value = true
  try {
    const res = await learningApi.getCalendar(84)
    calendarData.value = res.data || []
  } catch {
    calendarData.value = []
  } finally {
    calendarLoading.value = false
  }
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}分钟`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return `${hours}小时${rest > 0 ? `${rest}分钟` : ''}`
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function onDayClick(day: CalendarDay) {
  if (day.duration > 0) {
    const minutes = Math.round(day.duration / 60)
    const parts = [`${day.date}`, `学习 ${minutes} 分钟`]
    if (day.completed > 0) parts.push(`完成 ${day.completed} 门课`)
    showToast(parts.join(' | '))
  }
}

function goExamResult(recordId: number) {
  router.push(`/exam/result/${recordId}`)
}
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar title="学习记录" left-arrow fixed placeholder @click-left="router.back()" />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else>
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

      <div class="section-card">
        <div class="section-title">
          <span>学习日历</span>
          <span class="section-subtitle">最近 3 个月</span>
        </div>
        <CalendarHeatmap :data="calendarData" :loading="calendarLoading" @day-click="onDayClick" />
      </div>

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

              <div class="progress-detail">
                <div class="detail-row">
                  <span class="detail-label">今日学习</span>
                  <span class="detail-value">{{ formatDuration(learningStats.todayDuration) }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">总学习时长</span>
                  <span class="detail-value">{{ formatDuration(learningStats.totalDuration) }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">连续打卡</span>
                  <span class="detail-value">{{ learningStats.streakDays }} 天</span>
                </div>
              </div>
            </div>
          </van-tab>

          <van-tab title="考试记录">
            <div class="tab-content">
              <div class="trend-panel" v-if="trendData.length">
                <div class="section-title compact">
                  <span>成绩趋势</span>
                  <span class="section-subtitle">最近 {{ trendData.length }} 次</span>
                </div>
                <div class="trend-bars">
                  <div
                    v-for="item in trendData"
                    :key="item.recordId"
                    class="trend-item"
                    @click="goExamResult(item.recordId)"
                  >
                    <div
                      class="trend-bar"
                      :class="{ pass: item.passed, fail: !item.passed }"
                      :style="{ height: `${Math.max(8, Math.round((item.score / trendMaxScore) * 72))}px` }"
                    />
                    <span class="trend-score">{{ item.score }}</span>
                  </div>
                </div>
              </div>

              <div v-if="examRecords.length === 0" class="empty-tab">
                <span class="text-muted">暂无考试记录</span>
              </div>
              <div v-for="record in examRecords" :key="record.id" class="exam-record-item" @click="goExamResult(record.id)">
                <div class="record-left">
                  <div class="record-level" :class="record.passed ? 'pass' : 'fail'">
                    {{ levelLabels[record.examLevel] || record.examLevel }}
                  </div>
                  <div class="record-info">
                    <span class="record-title">{{ record.paperTitle || '考试' }}</span>
                    <span class="record-date">{{ formatDate(record.submittedAt) }}</span>
                  </div>
                </div>
                <div class="record-right">
                  <span class="record-score">{{ record.score }}分</span>
                  <van-tag round :color="record.passed ? 'var(--success)' : 'var(--danger)'" size="medium">
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
  text-align: center;
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text);

  &.compact {
    margin-bottom: 8px;
  }
}

.section-subtitle {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
}

.tab-content {
  padding: 16px 0;
  min-height: 100px;
}

.progress-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.progress-row,
.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-row {
  font-size: 14px;
}

.progress-text {
  color: var(--text-secondary);
}

.progress-value {
  font-weight: 600;
  color: var(--text);
}

.progress-detail {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-row {
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.detail-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.detail-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--primary);
}

.trend-panel {
  padding-bottom: 16px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--border-light);
}

.trend-bars {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 104px;
  overflow-x: auto;
  padding: 8px 2px 0;
}

.trend-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  min-width: 28px;
  height: 94px;
  cursor: pointer;
}

.trend-bar {
  width: 18px;
  border-radius: 6px 6px 2px 2px;

  &.pass {
    background: var(--success);
  }

  &.fail {
    background: var(--danger);
  }
}

.trend-score {
  font-size: 11px;
  color: var(--text-muted);
}

.empty-tab {
  text-align: center;
  padding: 24px 0;
}

.exam-record-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;

  &:last-child {
    border-bottom: none;
  }
}

.record-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
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
  flex-shrink: 0;

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
  min-width: 0;
}

.record-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-date {
  font-size: 12px;
  color: var(--text-muted);
}

.record-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.record-score {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}
</style>
