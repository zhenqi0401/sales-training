<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { learningApi, type LeaderboardPeriod } from '@/api/learning'
import { useAuthStore } from '@/stores/auth'
import type { Announcement, DailyTask, LeaderboardEntry, LearningStats, Video } from '@/types'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const taskLoading = ref(false)
const leaderboardLoading = ref(false)
const dailyTasks = ref<DailyTask[]>([])
const recentCourses = ref<Video[]>([])
const leaderboard = ref<LeaderboardEntry[]>([])
const announcements = ref<Announcement[]>([])
const leaderboardPeriod = ref<LeaderboardPeriod>('week')
const learningStats = ref<LearningStats>({
  completedVideos: 0,
  inProgressVideos: 0,
  pendingVideos: 0,
  totalVideos: 0,
  totalDuration: 0,
  todayDuration: 0,
  streakDays: 0
})

const periodOptions: Array<{ label: string; value: LeaderboardPeriod }> = [
  { label: '日榜', value: 'day' },
  { label: '周榜', value: 'week' },
  { label: '月榜', value: 'month' }
]

const progressPercent = computed(() => {
  if (!learningStats.value.totalVideos) return 0
  return Math.round((learningStats.value.completedVideos / learningStats.value.totalVideos) * 100)
})

const pendingRequiredTasks = computed(() => dailyTasks.value.filter((item) => !item.completed))

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 9) return '早上好'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

function formatDuration(minutes: number): string {
  if (minutes <= 0) return '0分钟'
  if (minutes < 60) return `${minutes}分钟`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h}小时${m ? `${m}分钟` : ''}`
}

function formatVideoDuration(seconds: number): string {
  const minutes = Math.max(1, Math.round(seconds / 60))
  return formatDuration(minutes)
}

async function loadHomeData() {
  loading.value = true
  try {
    const [tasksRes, recentRes, statsRes, announcementsRes] = await Promise.all([
      learningApi.getDailyTasks(),
      learningApi.getRecentCourses(),
      learningApi.getLearningStats(),
      learningApi.getAnnouncements()
    ])
    dailyTasks.value = tasksRes.data || []
    recentCourses.value = recentRes.data || []
    learningStats.value = {
      ...learningStats.value,
      ...(statsRes.data || {})
    }
    announcements.value = announcementsRes.data || []
    await loadLeaderboard()
  } catch {
    showToast('首页数据加载失败')
  } finally {
    loading.value = false
  }
}

async function loadLeaderboard() {
  leaderboardLoading.value = true
  try {
    const res = await learningApi.getLeaderboard(leaderboardPeriod.value)
    leaderboard.value = res.data || []
  } catch {
    leaderboard.value = []
  } finally {
    leaderboardLoading.value = false
  }
}

async function switchLeaderboardPeriod(period: LeaderboardPeriod) {
  if (leaderboardPeriod.value === period) return
  leaderboardPeriod.value = period
  await loadLeaderboard()
}

async function completeTask(task: DailyTask) {
  if (task.completed || taskLoading.value) return
  if (task.type === 'video') {
    router.push(`/courses/play/${task.targetId}`)
    return
  }
  taskLoading.value = true
  try {
    await learningApi.completeTask(task.id)
    task.completed = true
    showToast('任务已完成')
    const statsRes = await learningApi.getLearningStats()
    learningStats.value = { ...learningStats.value, ...(statsRes.data || {}) }
  } finally {
    taskLoading.value = false
  }
}

function goCourse(videoId: number) {
  router.push(`/courses/play/${videoId}`)
}

function goCourses() {
  router.push('/courses')
}

onMounted(loadHomeData)
</script>

<template>
  <div class="page home-page">
    <div class="home-header">
      <div class="header-row">
        <div>
          <div class="greeting-text">{{ greeting }}，{{ authStore.userName || '学员' }}</div>
          <div class="header-subtitle">今天还有 {{ pendingRequiredTasks.length }} 个必修任务待完成</div>
        </div>
        <div class="streak-badge" v-if="learningStats.streakDays > 0">
          <van-icon name="fire-o" size="14" />
          <span>连续 {{ learningStats.streakDays }} 天</span>
        </div>
      </div>

      <div class="overview-panel">
        <div class="overview-main">
          <span class="overview-value">{{ progressPercent }}%</span>
          <span class="overview-label">总体进度</span>
        </div>
        <div class="overview-progress">
          <van-progress
            :percentage="progressPercent"
            :stroke-width="8"
            color="#ffffff"
            track-color="rgba(255,255,255,0.26)"
            :show-pivot="false"
          />
        </div>
      </div>

      <div class="status-grid">
        <div class="status-item">
          <span class="status-num">{{ learningStats.completedVideos }}</span>
          <span class="status-label">已完成</span>
        </div>
        <div class="status-item">
          <span class="status-num">{{ learningStats.inProgressVideos }}</span>
          <span class="status-label">进行中</span>
        </div>
        <div class="status-item">
          <span class="status-num">{{ learningStats.pendingVideos }}</span>
          <span class="status-label">待开始</span>
        </div>
        <div class="status-item">
          <span class="status-num">{{ formatDuration(learningStats.todayDuration) }}</span>
          <span class="status-label">今日学习</span>
        </div>
      </div>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading">加载中...</van-loading>

    <template v-else>
      <section class="section-card">
        <div class="section-title">
          <span>今日学习任务</span>
          <span class="section-more">{{ pendingRequiredTasks.length }} 个待完成</span>
        </div>
        <div v-if="dailyTasks.length" class="task-list">
          <button
            v-for="task in dailyTasks"
            :key="task.id"
            class="task-item"
            :class="{ completed: task.completed }"
            type="button"
            @click="completeTask(task)"
          >
            <div class="task-icon">
              <van-icon :name="task.completed ? 'checked' : 'play-circle-o'" size="20" />
            </div>
            <div class="task-info">
              <div class="task-title">{{ task.title }}</div>
              <div class="task-desc">{{ task.description }}</div>
            </div>
            <van-tag v-if="task.completed" round plain type="success">已完成</van-tag>
            <van-tag v-else round color="var(--primary)">去学习</van-tag>
          </button>
        </div>
        <EmptyState v-else description="今日暂无必修课程" />
      </section>

      <section class="section-card">
        <div class="section-title">
          <span>最近学习的课程</span>
          <span class="section-more" @click="goCourses">全部课程</span>
        </div>
        <div v-if="recentCourses.length" class="recent-list">
          <button
            v-for="course in recentCourses"
            :key="course.id"
            class="recent-item"
            type="button"
            @click="goCourse(course.id)"
          >
            <van-image :src="course.cover" fit="cover" class="recent-cover" radius="6" />
            <div class="recent-info">
              <div class="recent-title">{{ course.title }}</div>
              <div class="recent-meta">
                <span>{{ formatVideoDuration(course.duration) }}</span>
                <span>{{ course.progress }}%</span>
              </div>
              <van-progress
                :percentage="course.progress"
                :stroke-width="4"
                color="linear-gradient(90deg, var(--primary), var(--success))"
                :show-pivot="false"
                track-color="#e8edf0"
              />
            </div>
            <van-icon name="arrow" size="16" color="var(--text-muted)" />
          </button>
        </div>
        <EmptyState v-else description="还没有学习记录" />
      </section>

      <section class="section-card">
        <div class="section-title">
          <span>学习排行榜</span>
          <div class="period-tabs">
            <button
              v-for="item in periodOptions"
              :key="item.value"
              type="button"
              class="period-tab"
              :class="{ active: leaderboardPeriod === item.value }"
              @click="switchLeaderboardPeriod(item.value)"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
        <van-loading v-if="leaderboardLoading" size="20" class="inline-loading" />
        <div v-else-if="leaderboard.length" class="leaderboard-list">
          <div
            v-for="entry in leaderboard.slice(0, 5)"
            :key="entry.userId"
            class="leader-item"
          >
            <div class="leader-rank" :class="{ gold: entry.rank === 1, silver: entry.rank === 2, bronze: entry.rank === 3 }">
              {{ entry.rank }}
            </div>
            <div class="leader-info">
              <span class="leader-name">{{ entry.name }}</span>
              <span class="leader-store">{{ entry.storeName }}</span>
            </div>
            <span class="leader-score">{{ entry.score }} 分</span>
          </div>
        </div>
        <EmptyState v-else description="暂无排行数据" />
      </section>

      <section class="section-card">
        <div class="section-title">
          <span>公告通知</span>
          <span class="section-more">{{ announcements.length }} 条</span>
        </div>
        <div v-if="announcements.length" class="notice-list">
          <div v-for="notice in announcements" :key="notice.id" class="notice-item">
            <div class="notice-dot" />
            <div class="notice-info">
              <div class="notice-title">{{ notice.title }}</div>
              <div class="notice-content">{{ notice.content }}</div>
            </div>
            <span class="notice-date">{{ notice.publishedAt }}</span>
          </div>
        </div>
        <EmptyState v-else description="暂无公告" />
      </section>


    </template>
  </div>
</template>

<style lang="scss" scoped>
.home-page {
  background: #eef7f5;
}

.home-header {
  padding: 20px 16px 18px;
  color: #fff;
  background: linear-gradient(135deg, #0e7490 0%, #0f766e 58%, #146c43 100%);
}

.header-row,
.status-grid,
.task-item,
.recent-item,
.leader-item,
.notice-item {
  display: flex;
  align-items: center;
}

.header-row {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.greeting-text {
  font-size: 22px;
  font-weight: 700;
}

.header-subtitle {
  margin-top: 6px;
  font-size: 13px;
  opacity: 0.86;
}

.streak-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  font-size: 12px;
  white-space: nowrap;
}

.overview-panel {
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.12);
}

.overview-main {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.overview-value {
  font-size: 30px;
  font-weight: 800;
}

.overview-label {
  font-size: 13px;
  opacity: 0.86;
}

.status-grid {
  justify-content: space-between;
  gap: 8px;
  margin-top: 14px;
}

.status-item {
  flex: 1;
  min-width: 0;
  padding: 10px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.13);
  text-align: center;
}

.status-num,
.status-label {
  display: block;
}

.status-num {
  min-height: 20px;
  font-size: 16px;
  font-weight: 700;
}

.status-label {
  margin-top: 3px;
  font-size: 11px;
  opacity: 0.84;
}

.page-loading,
.inline-loading {
  padding: 36px 0;
}

.section-card {
  border-radius: 8px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  color: var(--text);
  font-size: 16px;
  font-weight: 600;
}

.section-more {
  color: var(--primary);
  font-size: 12px;
  font-weight: 400;
}

.task-list,
.recent-list,
.leaderboard-list,
.notice-list {
  display: flex;
  flex-direction: column;
}

.task-item,
.recent-item {
  width: 100%;
  border: 0;
  background: transparent;
  text-align: left;
}

.task-item {
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: 0;
  }

  &.completed {
    opacity: 0.64;
  }
}

.task-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  color: var(--primary);
  background: #e6f6f4;
  flex-shrink: 0;
}

.task-info,
.recent-info,
.leader-info,
.notice-info {
  flex: 1;
  min-width: 0;
}

.task-title,
.recent-title,
.notice-title {
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.task-desc,
.recent-meta,
.notice-content {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.recent-item {
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: 0;
  }
}

.recent-cover {
  width: 76px;
  height: 46px;
  flex-shrink: 0;
  background: var(--border-light);
}

.recent-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 7px;
}

.period-tabs {
  display: flex;
  padding: 2px;
  border-radius: 8px;
  background: var(--border-light);
}

.period-tab {
  min-width: 38px;
  height: 24px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;

  &.active {
    background: #fff;
    color: var(--primary);
    font-weight: 600;
    box-shadow: var(--shadow-sm);
  }
}

.leader-item {
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: 0;
  }
}

.leader-rank {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--border);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;

  &.gold {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    color: #fff;
  }

  &.silver {
    background: linear-gradient(135deg, #94a3b8, #64748b);
    color: #fff;
  }

  &.bronze {
    background: linear-gradient(135deg, #b7791f, #92400e);
    color: #fff;
  }
}

.leader-name {
  display: block;
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.leader-store {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
}

.leader-score {
  color: var(--primary);
  font-size: 14px;
  font-weight: 700;
}

.notice-item {
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: 0;
  }
}

.notice-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--warning);
  flex-shrink: 0;
}

.notice-content {
  line-height: 1.5;
}

.notice-date {
  color: var(--text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 0 16px 16px;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-height: 72px;
  border: 0;
  border-radius: 8px;
  background: $card;
  box-shadow: var(--shadow-sm);

  span {
    color: var(--text-secondary);
    font-size: 12px;
  }
}
</style>
