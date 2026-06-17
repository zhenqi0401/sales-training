<template>
  <div class="page-container dashboard-page">
    <div class="page-header dashboard-header">
      <div>
        <h2>数据看板</h2>
        <p>聚焦学员视频学习进度、考试通过率与门店表现</p>
      </div>
      <div class="header-actions">
        <el-button :loading="loading" @click="loadData">刷新</el-button>
        <el-button type="primary" @click="handleExport">导出学员进度</el-button>
      </div>
    </div>

    <div v-if="loading" class="loading-wrap">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <template v-else>
      <section class="metric-grid section-gap">
        <el-card v-for="card in overviewCards" :key="card.label" shadow="hover" class="metric-card" :class="card.tone">
          <div class="metric-topline">{{ card.label }}</div>
          <div class="metric-value">{{ card.value }}</div>
          <div class="metric-sub">{{ card.sub }}</div>
        </el-card>
      </section>

      <section class="dashboard-grid section-gap">
        <el-card shadow="hover" class="focus-card">
          <template #header>
            <div class="card-header">
              <span>学习与考试达成</span>
              <span class="muted">全员汇总</span>
            </div>
          </template>
          <div class="ring-panel">
            <div class="ring-block">
              <div class="donut-chart learning" :style="ringStyle(data.overview.completionRate)">
                <div class="donut-core">
                  <strong>{{ data.overview.completionRate }}%</strong>
                  <span>完课率</span>
                </div>
              </div>
              <p>累计学习 {{ data.overview.totalWatchMinutes }} 分钟</p>
            </div>
            <div class="ring-block">
              <div class="donut-chart exam" :style="ringStyle(data.overview.examPassRate)">
                <div class="donut-core">
                  <strong>{{ data.overview.examPassRate }}%</strong>
                  <span>通过率</span>
                </div>
              </div>
              <p>平均分 {{ data.overview.averageScore }}，提交 {{ data.overview.totalExams }} 次</p>
            </div>
          </div>
          <div class="focus-strip">
            <div>
              <span>活跃学员</span>
              <strong>{{ data.overview.activeUsers }}</strong>
            </div>
            <div>
              <span>人均学习</span>
              <strong>{{ data.overview.averageLearningMinutes }} 分</strong>
            </div>
            <div>
              <span>视频数量</span>
              <strong>{{ data.overview.totalVideos }}</strong>
            </div>
          </div>
        </el-card>

        <el-card shadow="hover" class="store-chart-card">
          <template #header>
            <div class="card-header">
              <span>门店达成对比</span>
              <span class="muted">完成率 / 通过率</span>
            </div>
          </template>
          <div v-if="storeComparison.length" class="store-bars">
            <div v-for="item in storeComparison" :key="item.storeName" class="store-bar-row">
              <div class="store-name" :title="item.storeName">{{ item.storeName }}</div>
              <div class="bar-track">
                <div class="bar-fill learning" :style="{ width: `${clampPercent(item.completionRate)}%` }">
                  <span>{{ item.completionRate }}%</span>
                </div>
              </div>
              <div class="bar-track">
                <div class="bar-fill exam" :style="{ width: `${clampPercent(item.examPassRate)}%` }">
                  <span>{{ item.examPassRate }}%</span>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无门店数据" />
          <div class="legend">
            <span><i class="legend-dot learning" />学习完成率</span>
            <span><i class="legend-dot exam" />考试通过率</span>
          </div>
        </el-card>
      </section>

      <el-row :gutter="16" class="section-gap">
        <el-col :xs="24" :lg="12">
          <el-card shadow="hover" class="full-height">
            <template #header>
              <div class="card-header">
                <span>视频学习进度</span>
                <span class="muted">按完播率排序</span>
              </div>
            </template>
            <div v-if="videoRanking.length" class="ranking-list">
              <div v-for="(item, index) in videoRanking" :key="item.videoId" class="ranking-item">
                <span class="rank-index">{{ index + 1 }}</span>
                <div class="ranking-main">
                  <div class="ranking-title" :title="item.title">{{ item.title }}</div>
                  <div class="ranking-meta">{{ item.watchers }} 人观看 · 人均 {{ item.averageWatchMinutes }} 分</div>
                  <el-progress :percentage="item.completionRate" :stroke-width="8" />
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无视频学习数据" />
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12">
          <el-card shadow="hover" class="full-height">
            <template #header>
              <div class="card-header">
                <span>学员学习表现</span>
                <span class="muted">学习时长 Top 6</span>
              </div>
            </template>
            <el-table :data="learningRanking" height="340">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="name" label="学员" min-width="110" />
              <el-table-column prop="storeName" label="门店" min-width="120" show-overflow-tooltip />
              <el-table-column prop="watchMinutes" label="学习时长(分)" width="120" />
              <el-table-column prop="completionRate" label="完课率" width="140">
                <template #default="{ row }">
                  <el-progress :percentage="row.completionRate" :stroke-width="6" />
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="section-gap">
        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>门店学习完成率</span>
                <span class="muted">按完成率排序</span>
              </div>
            </template>
            <el-table :data="storeLearningRanking" height="320">
              <el-table-column prop="storeName" label="门店" min-width="140" show-overflow-tooltip />
              <el-table-column prop="studentCount" label="学员数" width="80" />
              <el-table-column prop="completionRate" label="完成率" min-width="160">
                <template #default="{ row }">
                  <el-progress :percentage="row.completionRate" :stroke-width="8" />
                </template>
              </el-table-column>
              <el-table-column prop="averageWatchMinutes" label="人均学习(分)" width="120" />
            </el-table>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>门店考试通过率</span>
                <span class="muted">按通过率排序</span>
              </div>
            </template>
            <el-table :data="storeExamRanking" height="320">
              <el-table-column prop="storeName" label="门店" min-width="140" show-overflow-tooltip />
              <el-table-column prop="studentCount" label="学员数" width="80" />
              <el-table-column prop="examPassRate" label="通过率" min-width="160">
                <template #default="{ row }">
                  <el-progress :percentage="row.examPassRate" :stroke-width="8" status="success" />
                </template>
              </el-table-column>
              <el-table-column prop="averageScore" label="平均分" width="90" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="hover" class="section-gap">
        <template #header>
          <div class="card-header">
            <span>学员学习进度列表</span>
            <span class="muted">共 {{ data.studentStats.progressList.length }} 人</span>
          </div>
        </template>
        <el-table :data="data.studentStats.progressList" height="420">
          <el-table-column prop="name" label="学员" min-width="110" fixed />
          <el-table-column prop="phone" label="手机号" min-width="130" />
          <el-table-column prop="storeName" label="门店" min-width="130" show-overflow-tooltip />
          <el-table-column prop="watchMinutes" label="学习时长(分)" width="120" sortable />
          <el-table-column label="视频进度" width="150">
            <template #default="{ row }">{{ row.completedVideos }}/{{ row.totalVideos }}</template>
          </el-table-column>
          <el-table-column prop="completionRate" label="完课率" width="150" sortable>
            <template #default="{ row }">
              <el-progress :percentage="row.completionRate" :stroke-width="6" />
            </template>
          </el-table-column>
          <el-table-column prop="examCount" label="考试次数" width="100" />
          <el-table-column prop="averageScore" label="平均分" width="100" sortable />
          <el-table-column prop="examPassRate" label="考试通过率" width="120">
            <template #default="{ row }">{{ row.examPassRate }}%</template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { exportStudentProgress, getDashboardData } from '@/api/dashboard'
import type { DashboardData } from '@/types'

const emptyData: DashboardData = {
  overview: {
    totalUsers: 0,
    activeUsers: 0,
    totalVideos: 0,
    totalQuestions: 0,
    totalStores: 0,
    totalExams: 0,
    completionRate: 0,
    totalWatchMinutes: 0,
    averageLearningMinutes: 0,
    examPassRate: 0,
    averageScore: 0,
    examPassRateByLevel: {},
  },
  videoStats: { items: [], ranking: [] },
  studentStats: { progressList: [], learningRanking: [], examRanking: [] },
  storeStats: [],
  examStats: {
    levels: [],
    papers: [],
    highFrequencyWrong: [],
    weakKnowledge: [],
    trend: [],
  },
}

const data = ref<DashboardData>(emptyData)
const loading = ref(true)

const overviewCards = computed(() => [
  { label: '学员总数', value: data.value.overview.totalUsers, sub: `活跃 ${data.value.overview.activeUsers} 人`, tone: 'tone-users' },
  { label: '视频完课率', value: `${data.value.overview.completionRate}%`, sub: `人均学习 ${data.value.overview.averageLearningMinutes} 分`, tone: 'tone-learning' },
  { label: '考试通过率', value: `${data.value.overview.examPassRate}%`, sub: `平均分 ${data.value.overview.averageScore}`, tone: 'tone-exam' },
  { label: '门店数量', value: data.value.overview.totalStores, sub: `覆盖 ${data.value.overview.totalVideos} 个视频`, tone: 'tone-store' },
])

const videoRanking = computed(() => {
  return [...data.value.videoStats.ranking]
    .sort((a, b) => b.completionRate - a.completionRate)
    .slice(0, 6)
})

const learningRanking = computed(() => {
  return data.value.studentStats.learningRanking.slice(0, 6)
})

const storeLearningRanking = computed(() => {
  return [...data.value.storeStats].sort((a, b) => b.completionRate - a.completionRate)
})

const storeExamRanking = computed(() => {
  return [...data.value.storeStats].sort((a, b) => b.examPassRate - a.examPassRate)
})

const storeComparison = computed(() => {
  return [...data.value.storeStats]
    .sort((a, b) => (b.completionRate + b.examPassRate) - (a.completionRate + a.examPassRate))
    .slice(0, 8)
})

function clampPercent(value: number) {
  return Math.min(100, Math.max(0, Number.isFinite(value) ? value : 0))
}

function ringStyle(value: number) {
  return { '--ring-value': `${clampPercent(value)}%` }
}

async function loadData() {
  loading.value = true
  try {
    data.value = await getDashboardData()
  } catch (error) {
    console.error(error)
    ElMessage.error('数据看板加载失败')
  } finally {
    loading.value = false
  }
}

async function handleExport() {
  try {
    await exportStudentProgress()
  } catch (error) {
    console.error(error)
    ElMessage.error('导出失败')
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.dashboard-page {
  background:
    linear-gradient(180deg, rgba(232, 245, 255, 0.72) 0%, rgba(240, 242, 245, 0) 260px),
    var(--bg-color);
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.loading-wrap {
  text-align: center;
  padding: 60px 0;
}

.section-gap {
  margin-bottom: 16px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.metric-card {
  position: relative;
  min-height: 126px;
  overflow: hidden;

  &::before {
    position: absolute;
    inset: 0 auto 0 0;
    width: 4px;
    content: '';
    background: var(--metric-color);
  }
}

.tone-users {
  --metric-color: #2f6fed;
}

.tone-learning {
  --metric-color: #11a683;
}

.tone-exam {
  --metric-color: #f59e0b;
}

.tone-store {
  --metric-color: #7c3aed;
}

.metric-topline {
  color: #606266;
  font-size: 13px;
}

.metric-value {
  margin-top: 10px;
  color: #1f2937;
  font-size: 30px;
  font-weight: 750;
  line-height: 1.1;
}

.metric-sub {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(360px, 0.9fr) minmax(0, 1.1fr);
  gap: 16px;
}

.full-height {
  height: 100%;
}

.card-header,
.legend {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.muted {
  color: #909399;
  font-size: 12px;
  font-weight: 400;
}

.ring-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.ring-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  padding: 10px 4px 4px;

  p {
    width: 100%;
    margin: 14px 0 0;
    color: #606266;
    font-size: 13px;
    line-height: 20px;
    text-align: center;
  }
}

.donut-chart {
  --ring-value: 0%;
  --ring-color: #409eff;
  display: grid;
  place-items: center;
  width: 174px;
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #fff 0 56%, transparent 57%),
    conic-gradient(var(--ring-color) var(--ring-value), #eef2f7 0);

  &.learning {
    --ring-color: #11a683;
  }

  &.exam {
    --ring-color: #f59e0b;
  }
}

.donut-core {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  strong {
    color: #1f2937;
    font-size: 30px;
    line-height: 1;
  }

  span {
    margin-top: 8px;
    color: #606266;
    font-size: 13px;
  }
}

.focus-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;

  div {
    min-width: 0;
    padding: 12px;
    border-radius: 8px;
    background: #f6f8fb;
  }

  span {
    display: block;
    color: #909399;
    font-size: 12px;
  }

  strong {
    display: block;
    margin-top: 6px;
    color: #303133;
    font-size: 16px;
  }
}

.store-bars {
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.store-bar-row {
  display: grid;
  grid-template-columns: minmax(86px, 120px) minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.store-name,
.ranking-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.store-name {
  color: #303133;
  font-size: 13px;
}

.bar-track {
  height: 22px;
  overflow: hidden;
  border-radius: 7px;
  background: #eef2f7;
}

.bar-fill {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 28px;
  height: 100%;
  padding-right: 6px;
  border-radius: 7px;
  color: #fff;
  font-size: 11px;
  line-height: 1;
  transition: width 0.2s ease;

  &.learning {
    background: #11a683;
  }

  &.exam {
    background: #f59e0b;
  }
}

.legend {
  justify-content: flex-end;
  margin-top: 16px;
  color: #606266;
  font-size: 12px;
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 5px;
  border-radius: 50%;

  &.learning {
    background: #11a683;
  }

  &.exam {
    background: #f59e0b;
  }
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ranking-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.rank-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #ecf5ff;
  color: #2f6fed;
  font-size: 13px;
  font-weight: 700;
}

.ranking-main {
  min-width: 0;
  flex: 1;
}

.ranking-title {
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.ranking-meta {
  margin: 5px 0 8px;
  color: #909399;
  font-size: 12px;
}

@media (max-width: 1200px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .dashboard-header,
  .header-actions {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;

    .el-button {
      width: 100%;
      margin-left: 0;
    }
  }

  .ring-panel,
  .focus-strip {
    grid-template-columns: 1fr;
  }

  .store-bar-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }
}

@media (max-width: 560px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .donut-chart {
    width: 150px;
  }
}
</style>
