<template>
  <div class="page-container">
    <div class="page-header dashboard-header">
      <div>
        <h2>数据看板</h2>
        <p>连接培训端学习、考试、错题和门店数据</p>
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
      <el-row :gutter="16" class="section-gap">
        <el-col v-for="card in overviewCards" :key="card.label" :xs="12" :sm="8" :lg="4">
          <el-card shadow="hover" class="metric-card">
            <div class="metric-value">{{ card.value }}</div>
            <div class="metric-label">{{ card.label }}</div>
            <div class="metric-sub" v-if="card.sub">{{ card.sub }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="section-gap">
        <el-col :xs="24" :lg="8">
          <el-card shadow="hover" class="full-height">
            <template #header>考试通过率</template>
            <div class="level-list">
              <div v-for="item in data.examStats.levels" :key="item.level" class="level-item">
                <div class="level-head">
                  <span>{{ item.level }}</span>
                  <strong>{{ item.passRate }}%</strong>
                </div>
                <el-progress :percentage="item.passRate" :stroke-width="8" />
                <div class="level-meta">平均分 {{ item.averageScore }} | {{ item.count }} 次考试</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="16">
          <el-card shadow="hover" class="full-height">
            <template #header>考试趋势</template>
            <div class="trend-chart">
              <div
                v-for="item in data.examStats.trend"
                :key="item.date"
                class="trend-item"
                :title="`${item.date} 平均分 ${item.averageScore} 通过率 ${item.passRate}%`"
              >
                <div class="trend-bar-wrap">
                  <div class="trend-bar pass" :style="{ height: `${Math.max(4, item.passRate * 0.78)}px` }" />
                  <div class="trend-bar score" :style="{ height: `${Math.max(4, item.averageScore * 0.78)}px` }" />
                </div>
                <span>{{ item.date.slice(5) }}</span>
              </div>
            </div>
            <div class="legend">
              <span><i class="legend-dot pass" />通过率</span>
              <span><i class="legend-dot score" />平均分</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="section-gap">
        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>视频学习排行</template>
            <el-table :data="data.videoStats.ranking" height="320">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="title" label="视频" min-width="180" show-overflow-tooltip />
              <el-table-column prop="watchers" label="观看人数" width="90" />
              <el-table-column prop="completionRate" label="完播率" width="130">
                <template #default="{ row }">
                  <el-progress :percentage="row.completionRate" :stroke-width="6" />
                </template>
              </el-table-column>
              <el-table-column prop="averageWatchMinutes" label="均时长(分)" width="100" />
            </el-table>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>视频维度明细</template>
            <el-table :data="data.videoStats.items" height="320">
              <el-table-column prop="title" label="视频" min-width="180" show-overflow-tooltip />
              <el-table-column prop="categoryName" label="分类" width="100" />
              <el-table-column prop="watchers" label="观看人数" width="90" />
              <el-table-column prop="totalWatchMinutes" label="总时长(分)" width="110" />
              <el-table-column prop="completionRate" label="完播率" width="90">
                <template #default="{ row }">{{ row.completionRate }}%</template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="section-gap">
        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>学员学习时长排行</template>
            <el-table :data="data.studentStats.learningRanking" height="320">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="name" label="学员" min-width="110" />
              <el-table-column prop="storeName" label="门店" min-width="120" show-overflow-tooltip />
              <el-table-column prop="watchMinutes" label="学习时长(分)" width="120" />
              <el-table-column prop="completionRate" label="完课率" width="130">
                <template #default="{ row }">
                  <el-progress :percentage="row.completionRate" :stroke-width="6" />
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>学员考试成绩排行</template>
            <el-table :data="data.studentStats.examRanking" height="320">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="name" label="学员" min-width="110" />
              <el-table-column prop="storeName" label="门店" min-width="120" show-overflow-tooltip />
              <el-table-column prop="bestScore" label="最高分" width="90" />
              <el-table-column prop="averageScore" label="平均分" width="90" />
              <el-table-column prop="examPassRate" label="通过率" width="90">
                <template #default="{ row }">{{ row.examPassRate }}%</template>
              </el-table-column>
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

      <el-row :gutter="16" class="section-gap">
        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>门店学习完成率对比</template>
            <el-table :data="data.storeStats" height="320">
              <el-table-column prop="storeName" label="门店" min-width="140" show-overflow-tooltip />
              <el-table-column prop="studentCount" label="学员数" width="80" />
              <el-table-column prop="completionRate" label="完成率" min-width="160">
                <template #default="{ row }">
                  <el-progress :percentage="row.completionRate" :stroke-width="8" />
                </template>
              </el-table-column>
              <el-table-column prop="averageWatchMinutes" label="均时长(分)" width="110" />
            </el-table>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>门店考试通过率对比</template>
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

      <el-row :gutter="16" class="section-gap">
        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>各试卷/等级统计</template>
            <el-table :data="data.examStats.papers" height="320">
              <el-table-column prop="paperTitle" label="试卷" min-width="160" show-overflow-tooltip />
              <el-table-column prop="level" label="等级" width="70" />
              <el-table-column prop="count" label="次数" width="70" />
              <el-table-column prop="averageScore" label="平均分" width="90" />
              <el-table-column prop="passRate" label="通过率" width="90">
                <template #default="{ row }">{{ row.passRate }}%</template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="12">
          <el-card shadow="hover">
            <template #header>错题分析</template>
            <div class="wrong-layout">
              <div>
                <h4>高频错题排行</h4>
                <el-table :data="data.examStats.highFrequencyWrong" height="240">
                  <el-table-column prop="content" label="题目" min-width="180" show-overflow-tooltip />
                  <el-table-column prop="categoryName" label="知识点" width="100" />
                  <el-table-column prop="wrongCount" label="错误次数" width="90" />
                </el-table>
              </div>
              <div>
                <h4>薄弱知识点</h4>
                <div class="weak-tags">
                  <el-tag v-for="item in data.examStats.weakKnowledge" :key="item.name" type="danger" effect="plain">
                    {{ item.name }} {{ item.wrongCount }}
                  </el-tag>
                  <el-empty v-if="data.examStats.weakKnowledge.length === 0" description="暂无错题数据" />
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
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
  { label: '学员总数', value: data.value.overview.totalUsers, sub: `活跃 ${data.value.overview.activeUsers}` },
  { label: '完课率', value: `${data.value.overview.completionRate}%`, sub: '按学员 x 视频统计' },
  { label: '视频总时长', value: `${data.value.overview.totalWatchMinutes} 分`, sub: `人均 ${data.value.overview.averageLearningMinutes} 分` },
  { label: '考试通过率', value: `${data.value.overview.examPassRate}%`, sub: `平均分 ${data.value.overview.averageScore}` },
  { label: '试卷提交', value: data.value.overview.totalExams, sub: '培训端考试记录' },
  { label: '门店数量', value: data.value.overview.totalStores, sub: `视频 ${data.value.overview.totalVideos} | 题目 ${data.value.overview.totalQuestions}` },
])

const storeExamRanking = computed(() => {
  return [...data.value.storeStats].sort((a, b) => b.examPassRate - a.examPassRate)
})

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

.metric-card {
  min-height: 118px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.metric-label {
  margin-top: 8px;
  font-size: 14px;
  color: #606266;
}

.metric-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.full-height {
  height: 100%;
}

.level-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.level-head,
.card-header,
.legend {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.level-meta,
.muted {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.trend-chart {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  min-height: 140px;
  overflow-x: auto;
  padding: 12px 4px 4px;
}

.trend-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 36px;
  font-size: 11px;
  color: #909399;
}

.trend-bar-wrap {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 86px;
}

.trend-bar {
  width: 8px;
  min-height: 4px;
  border-radius: 4px 4px 0 0;

  &.pass {
    background: #67c23a;
  }

  &.score {
    background: #409eff;
  }
}

.legend {
  justify-content: flex-end;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  color: #606266;
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;

  &.pass {
    background: #67c23a;
  }

  &.score {
    background: #409eff;
  }
}

.wrong-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(180px, 0.8fr);
  gap: 16px;

  h4 {
    margin: 0 0 10px;
    font-size: 14px;
    color: #303133;
  }
}

.weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-content: flex-start;
  min-height: 240px;
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

  .wrong-layout {
    grid-template-columns: 1fr;
  }
}
</style>
