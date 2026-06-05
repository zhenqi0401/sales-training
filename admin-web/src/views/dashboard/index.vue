<template>
  <div class="page-container">
    <div class="page-header">
      <h2>数据看板</h2>
      <p>系统运营数据概览</p>
    </div>

    <!-- Stat Cards -->
    <el-row :gutter="20" class="stat-row">
      <el-col :xs="12" :sm="12" :md="8" :lg="4" v-for="stat in statCards" :key="stat.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-card-content">
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
            <el-icon class="stat-icon" :size="40" :color="stat.color">
              <component :is="stat.icon" />
            </el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Loading / error state -->
    <div v-if="loading" style="text-align:center;padding:40px"><el-icon class="is-loading" :size="32"><Loading /></el-icon></div>

    <!-- Charts Row -->
    <el-row v-if="!loading" :gutter="20" class="charts-row">
      <el-col :xs="24" :lg="16">
        <el-card shadow="hover">
          <template #header><span>用户增长趋势</span></template>
          <div class="chart-placeholder">
            <el-empty description="接入数据后将展示近30天用户增长曲线" />
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="hover">
          <template #header><span>学习完成率</span></template>
          <div class="progress-stat">
            <el-progress type="dashboard" :percentage="stats.completionRate" :width="160" color="#409eff">
              <template #default>
                <span class="progress-value">{{ stats.completionRate }}%</span>
              </template>
            </el-progress>
            <p class="progress-label">总体学习完成率</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Bottom Row -->
    <el-row v-if="!loading" :gutter="20" class="charts-row">
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header><span>系统概览</span></template>
          <div class="stats-grid">
            <div class="stats-grid-item">
              <div class="num">{{ stats.totalExams }}</div>
              <div class="txt">考试提交总数</div>
            </div>
            <div class="stats-grid-item">
              <div class="num">{{ stats.examPassRate }}%</div>
              <div class="txt">考试通过率</div>
            </div>
            <div class="stats-grid-item">
              <div class="num">{{ stats.averageScore ?? '--' }}</div>
              <div class="txt">平均分</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header><span>快捷入口</span></template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/users')">学员管理</el-button>
            <el-button type="success" @click="$router.push('/videos')">视频管理</el-button>
            <el-button type="warning" @click="$router.push('/questions')">题库管理</el-button>
            <el-button @click="$router.push('/exams')">试卷管理</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getDashboardStats } from '@/api/dashboard'
import type { DashboardStats } from '@/types'

const stats = ref<DashboardStats>({
  totalUsers: 0, activeUsers: 0, totalVideos: 0, totalQuestions: 0,
  totalStores: 0, examPassRate: 0, completionRate: 0, totalExams: 0,
})
const loading = ref(true)

const statCards = ref([
  { label: '总用户数', value: '--', icon: 'User', color: '#409eff' },
  { label: '今日活跃', value: '--', icon: 'Avatar', color: '#67c23a' },
  { label: '视频总数', value: '--', icon: 'VideoCamera', color: '#e6a23c' },
  { label: '题目总数', value: '--', icon: 'Document', color: '#f56c6c' },
  { label: '门店总数', value: '--', icon: 'Shop', color: '#909399' },
  { label: '考试通过率', value: '--', icon: 'TrendCharts', color: '#409eff' },
])

function updateStatCards(data: DashboardStats) {
  statCards.value = [
    { label: '总用户数', value: String(data.totalUsers ?? 0), icon: 'User', color: '#409eff' },
    { label: '今日活跃', value: String(data.activeUsers ?? 0), icon: 'Avatar', color: '#67c23a' },
    { label: '视频总数', value: String(data.totalVideos ?? 0), icon: 'VideoCamera', color: '#e6a23c' },
    { label: '题目总数', value: String(data.totalQuestions ?? 0), icon: 'Document', color: '#f56c6c' },
    { label: '门店总数', value: String(data.totalStores ?? 0), icon: 'Shop', color: '#909399' },
    { label: '考试通过率', value: (data.examPassRate ?? 0) + '%', icon: 'TrendCharts', color: '#409eff' },
  ]
}

onMounted(async () => {
  try {
    const data = await getDashboardStats()
    // Backend uses snake_case; interceptor normalizes page responses but this is a raw dict.
    // Handle both cases.
    stats.value = {
      totalUsers: (data as any).total_users ?? data.totalUsers ?? 0,
      activeUsers: (data as any).active_users ?? data.activeUsers ?? 0,
      totalVideos: (data as any).total_videos ?? data.totalVideos ?? 0,
      totalQuestions: (data as any).total_questions ?? data.totalQuestions ?? 0,
      totalStores: (data as any).total_stores ?? data.totalStores ?? 0,
      totalExams: (data as any).total_exams ?? 0,
      examPassRate: (data as any).exam_pass_rate ?? data.examPassRate ?? 0,
      completionRate: (data as any).completion_rate ?? data.completionRate ?? 0,
    }
    updateStatCards(stats.value)
  } catch (e) {
    console.error('Dashboard fetch error:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped lang="scss">
.stat-row { margin-bottom: 20px; }

.stat-card-content {
  display: flex; justify-content: space-between; align-items: center;
  .stat-info {
    .stat-value { font-size: 28px; font-weight: 700; color: #303133; margin-bottom: 4px; }
    .stat-label { font-size: 14px; color: #909399; }
  }
}

.charts-row { margin-bottom: 20px; }

.chart-placeholder {
  display: flex; flex-direction: column; align-items: center; padding: 20px 0;
}

.progress-stat {
  display: flex; flex-direction: column; align-items: center; padding: 10px 0;
  .progress-value { font-size: 24px; font-weight: 700; color: #303133; }
  .progress-label { font-size: 14px; color: #909399; margin: 12px 0 0; }
}

.stats-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; padding: 8px;
  .stats-grid-item { text-align: center;
    .num { font-size: 24px; font-weight: 700; color: #303133; }
    .txt { font-size: 12px; color: #909399; margin-top: 4px; }
  }
}

.quick-actions { display: flex; flex-wrap: wrap; gap: 12px; padding: 8px; }
</style>
