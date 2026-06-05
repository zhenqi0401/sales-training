<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { learningApi } from '@/api/learning'
import type { DailyTask, LeaderboardEntry, Category } from '@/types'
import { showToast } from 'vant'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const dailyTasks = ref<DailyTask[]>([])
const leaderboard = ref<LeaderboardEntry[]>([])
const categories = ref<Category[]>([])
const learningStats = ref({
  completedVideos: 0,
  totalVideos: 0,
  todayDuration: 0,
  streakDays: 0
})

const greeting = ref('')

function setGreeting() {
  const hour = new Date().getHours()
  if (hour < 6) greeting.value = '夜深了'
  else if (hour < 9) greeting.value = '早上好'
  else if (hour < 12) greeting.value = '上午好'
  else if (hour < 14) greeting.value = '中午好'
  else if (hour < 18) greeting.value = '下午好'
  else greeting.value = '晚上好'
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}分钟`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h}小时${m > 0 ? `${m}分钟` : ''}`
}

const categoryIcons: Record<string, string> = {
  qingkong: 'eye-o',
  xieruoshi: 'medical-o',
  jiaosu: 'aiming-o',
  yanjing: 'glasses-o',
  zhoubian: 'gift-o',
  gongneng: 'gem-o',
  qiwenhua: 'fire-o'
}

const categoryNames: Record<string, string> = {
  qingkong: '青控',
  xieruoshi: '斜弱视',
  jiaosu: '角塑',
  yanjing: '眼镜',
  zhoubian: '周边产品',
  gongneng: '功能性眼镜',
  qiwenhua: '企业文化'
}

const categoryColors: Record<string, string> = {
  qingkong: '#0e7490',
  xieruoshi: '#7c3aed',
  jiaosu: '#0891b2',
  yanjing: '#059669',
  zhoubian: '#d97706',
  gongneng: '#dc2626',
  qiwenhua: '#4f46e5'
}

onMounted(async () => {
  setGreeting()
  try {
    const [tasksRes, lbRes, statsRes, catRes] = await Promise.all([
      learningApi.getDailyTasks(),
      learningApi.getLeaderboard(),
      learningApi.getLearningStats(),
      learningApi.getCategories()
    ])
    dailyTasks.value = tasksRes.data || []
    leaderboard.value = lbRes.data || []
    learningStats.value = statsRes.data || { completedVideos: 0, totalVideos: 0, todayDuration: 0, streakDays: 0 }
    categories.value = catRes.data || []
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

function goCategory(categoryId: number) {
  router.push(`/courses/list/${categoryId}`)
}

function goExam() {
  router.push('/exam')
}

function goCourse(id: number) {
  router.push(`/courses/play/${id}`)
}
</script>

<template>
  <div class="page">
    <!-- Header Section -->
    <div class="home-header bg-gradient-primary">
      <div class="header-greeting">
        <div class="greeting-text">{{ greeting }}，{{ authStore.userName || '学员' }}</div>
        <div class="streak-badge" v-if="learningStats.streakDays > 0">
          <van-icon name="fire-o" size="14" color="#f59e0b" />
          <span>连续{{ learningStats.streakDays }}天</span>
        </div>
      </div>
      <div class="header-stats">
        <div class="stat-block">
          <span class="stat-num">{{ learningStats.completedVideos }}</span>
          <span class="stat-label">已完成课程</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-block">
          <span class="stat-num">{{ formatDuration(learningStats.todayDuration) }}</span>
          <span class="stat-label">今日学习</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-block">
          <span class="stat-num">{{ learningStats.totalVideos }}</span>
          <span class="stat-label">总课程</span>
        </div>
      </div>
    </div>

    <!-- Quick Categories -->
    <div class="section-card">
      <div class="section-title">
        <span>课程分类</span>
        <span class="section-more" @click="router.push('/courses')">全部</span>
      </div>
      <div class="category-grid">
        <div
          v-for="cat in categories.slice(0, 7)"
          :key="cat.id"
          class="category-item"
          @click="goCategory(cat.id)"
        >
          <div
            class="category-icon"
            :style="{ background: categoryColors[cat.code] || 'var(--primary)' }"
          >
            <van-icon :name="categoryIcons[cat.code] || 'label-o'" size="22" color="#fff" />
          </div>
          <span class="category-name">{{ categoryNames[cat.code] || cat.name }}</span>
        </div>
      </div>
    </div>

    <!-- Daily Tasks -->
    <div class="section-card" v-if="dailyTasks.length > 0">
      <div class="section-title">
        <span>今日任务</span>
        <span class="section-more">完成得积分</span>
      </div>
      <div class="task-list">
        <div
          v-for="task in dailyTasks"
          :key="task.id"
          class="task-item"
          :class="{ completed: task.completed }"
        >
          <div class="task-info">
            <div class="task-title">{{ task.title }}</div>
            <div class="task-desc">{{ task.description }}</div>
          </div>
          <div class="task-status">
            <van-icon
              v-if="task.completed"
              name="checked"
              color="var(--success)"
              size="20"
            />
            <van-tag v-else round color="var(--primary)" size="small">去完成</van-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- Leaderboard -->
    <div class="section-card" v-if="leaderboard.length > 0">
      <div class="section-title">
        <span>学习排行榜</span>
        <span class="section-more">本周</span>
      </div>
      <div class="leaderboard-list">
        <div
          v-for="(entry, idx) in leaderboard.slice(0, 5)"
          :key="entry.userId"
          class="leader-item"
        >
          <div class="leader-rank" :class="{ gold: idx === 0, silver: idx === 1, bronze: idx === 2 }">
            {{ idx + 1 }}
          </div>
          <div class="leader-info">
            <span class="leader-name">{{ entry.name }}</span>
            <span class="leader-store">{{ entry.storeName }}</span>
          </div>
          <span class="leader-score">{{ entry.score }}分</span>
        </div>
      </div>
    </div>

    <!-- Quick action buttons -->
    <div class="quick-actions">
      <div class="action-btn" @click="router.push('/practice')">
        <van-icon name="fire-o" size="24" color="var(--primary)" />
        <span>实战演练</span>
      </div>
      <div class="action-btn" @click="router.push('/scripts')">
        <van-icon name="chat-o" size="24" color="var(--primary)" />
        <span>销售话术</span>
      </div>
      <div class="action-btn" @click="router.push('/exam')">
        <van-icon name="records-o" size="24" color="var(--primary)" />
        <span>模拟考试</span>
      </div>
      <div class="action-btn" @click="goExam">
        <van-icon name="flash-o" size="24" color="var(--warning)" />
        <span>冲刺模式</span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.home-header {
  padding: 20px 20px 24px;
  color: #fff;
}

.header-greeting {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.greeting-text {
  font-size: 22px;
  font-weight: 700;
}

.streak-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
}

.header-stats {
  display: flex;
  align-items: center;
  justify-content: space-around;
}

.stat-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-num {
  font-size: 18px;
  font-weight: 700;
}

.stat-label {
  font-size: 12px;
  opacity: 0.85;
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: rgba(255, 255, 255, 0.3);
}

.section-card {
  background: $card;
  border-radius: $radius;
  margin: 12px 16px;
  padding: 16px;
  box-shadow: var(--shadow-sm);
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 14px;
}

.section-more {
  font-size: 12px;
  color: var(--primary);
  font-weight: 400;
}

// Category grid
.category-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px 8px;
}

.category-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;

  &:active {
    opacity: 0.7;
  }
}

.category-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.category-name {
  font-size: 11px;
  color: var(--text-secondary);
  text-align: center;
}

// Tasks
.task-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: none;
  }

  &.completed {
    opacity: 0.6;
  }
}

.task-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.task-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

// Leaderboard
.leaderboard-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.leader-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: none;
  }
}

.leader-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  background: var(--border);
  color: var(--text-muted);
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
    background: linear-gradient(135deg, #d97706, #b45309);
    color: #fff;
  }
}

.leader-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.leader-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.leader-store {
  font-size: 12px;
  color: var(--text-muted);
}

.leader-score {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary);
}

// Quick actions
.quick-actions {
  display: flex;
  justify-content: space-around;
  padding: 8px 16px 16px;
  gap: 8px;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  background: $card;
  border-radius: $radius;
  flex: 1;
  box-shadow: var(--shadow-sm);

  &:active {
    opacity: 0.7;
  }

  span {
    font-size: 11px;
    color: var(--text-secondary);
  }
}
</style>
