<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showToast } from 'vant'
import { salesApi } from '@/api/sales'

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
const totalSalesCount = ref(0)
const totalMethodologyCount = ref(0)

const currentMethodologies = ref<Methodology[]>([])
const currentName = ref('')
const showMethodPopup = ref(false)

async function loadData() {
  loading.value = true
  try {
    const res = await salesApi.getSalesList()
    const data = res.data || []
    salesList.value = data
    totalSalesCount.value = data.length
    totalMethodologyCount.value = data.reduce((sum, s) => sum + s.methodology_count, 0)
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

function openMethodology(item: SalesUser) {
  currentName.value = item.real_name || item.username
  currentMethodologies.value = item.methodologies
  showMethodPopup.value = true
}

onMounted(loadData)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">销售看板</h2>
      <p class="page-subtitle">销售团队业绩与方法论概览</p>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading">加载中...</van-loading>

    <template v-else>
      <div class="summary-stats">
        <div class="summary-item">
          <span class="summary-num">{{ totalSalesCount }}</span>
          <span class="summary-label">销售人员</span>
        </div>
        <div class="summary-item">
          <span class="summary-num">{{ totalMethodologyCount }}</span>
          <span class="summary-label">方法论总数</span>
        </div>
      </div>

      <div v-if="salesList.length" class="sales-grid">
        <div v-for="item in salesList" :key="item.id" class="sales-card">
          <div class="card-avatar">
            <van-image
              round
              width="48"
              height="48"
              :src="item.avatar || undefined"
            >
              <template #error>
                <div class="avatar-placeholder">{{ (item.real_name || item.username).charAt(0) }}</div>
              </template>
            </van-image>
          </div>
          <div class="card-info">
            <div class="card-name">{{ item.real_name || item.username }}</div>
            <div class="card-stats">
              <div class="stat">
                <span class="stat-num">{{ item.sales_count }}</span>
                <span class="stat-label">销售</span>
              </div>
              <div class="stat">
                <span class="stat-num">{{ item.deal_count }}</span>
                <span class="stat-label">成交</span>
              </div>
              <div class="stat">
                <span class="stat-num">{{ item.methodology_count }}</span>
                <span class="stat-label">方法论</span>
              </div>
            </div>
          </div>
          <van-button
            size="small"
            type="primary"
            :disabled="!item.methodology_count"
            @click="openMethodology(item)"
          >
            方法论
          </van-button>
        </div>
      </div>
      <van-empty v-else description="暂无销售人员" />
    </template>

    <!-- Methodology Popup -->
    <van-popup v-model:show="showMethodPopup" position="bottom" round :style="{ height: '70%' }">
      <div class="popup-panel">
        <div class="popup-header">
          <span class="popup-title">{{ currentName }} 的方法论</span>
          <van-icon name="cross" size="20" @click="showMethodPopup = false" />
        </div>
        <div v-if="currentMethodologies.length" class="popup-body">
          <div v-for="m in currentMethodologies" :key="m.id" class="method-item">
            <div class="method-title">{{ m.title }}</div>
            <div class="method-content">{{ m.content }}</div>
            <div class="method-meta">
              <van-tag round plain type="primary">{{ m.source || '手动' }}</van-tag>
              <span class="method-date">{{ m.created_at?.slice(0, 10) }}</span>
            </div>
          </div>
        </div>
        <van-empty v-else description="暂无方法论" />
      </div>
    </van-popup>
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
.page-loading {
  padding: 36px 0;
  display: block;
  text-align: center;
}

.summary-stats {
  display: flex;
  padding: 12px 16px;
  gap: 12px;
}
.summary-item {
  flex: 1;
  background: $card;
  border-radius: $radius;
  padding: 12px 8px;
  text-align: center;
  box-shadow: var(--shadow-sm);
}
.summary-num {
  font-size: 24px;
  font-weight: 700;
  color: var(--primary);
  display: block;
}
.summary-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.sales-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  padding: 0 16px 16px;
}

.sales-card {
  background: $card;
  border-radius: $radius;
  padding: 14px 10px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.card-avatar {
  flex-shrink: 0;
}

.avatar-placeholder {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
}

.card-info {
  text-align: center;
  width: 100%;
}

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
}

.card-stats {
  display: flex;
  justify-content: center;
  gap: 14px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  font-size: 10px;
  color: var(--text-muted);
}

.popup-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.popup-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
}

.popup-body {
  flex: 1;
  overflow-y: auto;
}

.method-item {
  padding: 12px;
  background: $bg;
  border-radius: 8px;
  margin-bottom: 8px;
}

.method-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.method-content {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
  white-space: pre-wrap;
}

.method-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.method-date {
  font-size: 10px;
  color: var(--text-muted);
}
</style>
