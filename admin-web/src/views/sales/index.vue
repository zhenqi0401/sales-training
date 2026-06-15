<template>
  <div class="page-container">
    <div class="page-header">
      <h2>销售管理</h2>
      <p>管理销售团队，查看各销售人员的业绩和方法论总结</p>
    </div>

    <div v-if="loading" class="loading-wrap">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <template v-else>
      <div v-if="salesList.length" class="sales-grid">
        <div v-for="item in salesList" :key="item.id" class="sales-card">
          <div class="card-avatar">
            <el-avatar :size="56" :src="item.avatar" :icon="'UserFilled'" />
          </div>
          <div class="card-info">
            <div class="card-name">{{ item.real_name || item.username }}</div>
            <div class="card-phone">{{ item.phone }}</div>
            <div class="card-stats">
              <div class="stat-item">
                <span class="stat-num">{{ item.sales_count }}</span>
                <span class="stat-label">销售次数</span>
              </div>
              <div class="stat-item">
                <span class="stat-num">{{ item.deal_count }}</span>
                <span class="stat-label">成交次数</span>
              </div>
              <div class="stat-item">
                <span class="stat-num">{{ item.methodology_count }}</span>
                <span class="stat-label">方法论</span>
              </div>
            </div>
          </div>
          <div class="card-actions">
            <el-button
              type="primary"
              size="small"
              :disabled="!item.methodology_count"
              @click="openMethodology(item)"
            >
              查看方法论
            </el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无销售人员" />
    </template>

    <!-- Methodology Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="currentSales ? `${currentSales.real_name || currentSales.username} 的方法论` : '方法论'"
      width="640px"
    >
      <div v-if="currentMethodologies.length" class="methodology-list">
        <div v-for="m in currentMethodologies" :key="m.id" class="methodology-item">
          <div class="methodology-title">{{ m.title }}</div>
          <div class="methodology-content">{{ m.content }}</div>
          <div class="methodology-meta">
            <span v-if="m.source" class="methodology-source">{{ m.source }}</span>
            <span class="methodology-date">{{ m.created_at?.slice(0, 10) }}</span>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无方法论" />
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSalesList } from '@/api/sales'

interface Methodology {
  id: number
  title: string
  content: string
  source: string
  created_at: string
}

interface SalesUser {
  id: number
  username: string
  real_name: string
  avatar: string
  phone: string
  sales_count: number
  deal_count: number
  methodology_count: number
  methodologies: Methodology[]
}

const loading = ref(true)
const salesList = ref<SalesUser[]>([])
const dialogVisible = ref(false)
const currentSales = ref<SalesUser | null>(null)
const currentMethodologies = ref<Methodology[]>([])

async function loadData() {
  loading.value = true
  try {
    const res = await getSalesList()
    salesList.value = res.data || []
  } catch {
    ElMessage.error('加载销售列表失败')
  } finally {
    loading.value = false
  }
}

function openMethodology(item: SalesUser) {
  currentSales.value = item
  currentMethodologies.value = item.methodologies
  dialogVisible.value = true
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.sales-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 16px 0;

  @media (max-width: 1400px) {
    grid-template-columns: repeat(3, 1fr);
  }
  @media (max-width: 1000px) {
    grid-template-columns: repeat(2, 1fr);
  }
  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
}

.sales-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px 16px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  }
}

.card-avatar {
  flex-shrink: 0;
}

.card-info {
  text-align: center;
  width: 100%;
}

.card-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}

.card-phone {
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
}

.card-stats {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
}

.stat-label {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.card-actions {
  width: 100%;
  display: flex;
  justify-content: center;
}

.methodology-list {
  max-height: 420px;
  overflow-y: auto;
}

.methodology-item {
  padding: 14px;
  border-bottom: 1px solid #ebeef5;

  &:last-child {
    border-bottom: none;
  }
}

.methodology-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.methodology-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  white-space: pre-wrap;
}

.methodology-meta {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.methodology-source {
  font-size: 11px;
  color: #409eff;
  background: #ecf5ff;
  padding: 1px 6px;
  border-radius: 3px;
}

.methodology-date {
  font-size: 11px;
  color: #c0c4cc;
}

.loading-wrap {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}
</style>
