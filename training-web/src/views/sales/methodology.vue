<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showToast } from 'vant'
import { salesApi } from '@/api/sales'

interface Methodology {
  id: number
  title: string
  content: string
  source: string
  tags: string
  status: string
  created_at: string
}

const loading = ref(true)
const methodologies = ref<Methodology[]>([])
const total = ref(0)
const page = ref(1)
const selectedItem = ref<Methodology | null>(null)
const showDetail = ref(false)

async function loadMethodologies() {
  loading.value = true
  try {
    const res = await salesApi.getMethodologies(page.value)
    const data = res.data
    methodologies.value = data.items || []
    total.value = data.total || 0
  } catch {
    showToast('方法论加载失败')
  } finally {
    loading.value = false
  }
}

function openDetail(item: Methodology) {
  selectedItem.value = item
  showDetail.value = true
}

onMounted(loadMethodologies)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">销售方法论</h2>
      <p class="page-subtitle">沉淀销售经验，共享优秀话术</p>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading">加载中...</van-loading>

    <template v-else>
      <div v-if="methodologies.length" class="method-list">
        <div
          v-for="item in methodologies"
          :key="item.id"
          class="method-card"
          @click="openDetail(item)"
        >
          <div class="method-title">{{ item.title }}</div>
          <div class="method-preview">{{ item.content.slice(0, 80) }}{{ item.content.length > 80 ? '...' : '' }}</div>
          <div class="method-meta">
            <van-tag round plain type="primary" size="small">{{ item.source || '手动创建' }}</van-tag>
            <span class="method-date">{{ item.created_at?.slice(0, 10) }}</span>
          </div>
        </div>
      </div>
      <van-empty v-else description="暂无销售方法论" />
    </template>

    <van-popup v-model:show="showDetail" position="bottom" round :style="{ height: '75%' }">
      <div v-if="selectedItem" class="detail-panel">
        <div class="detail-header">
          <span class="detail-title">{{ selectedItem.title }}</span>
          <van-icon name="cross" size="20" @click="showDetail = false" />
        </div>
        <div class="detail-content">{{ selectedItem.content }}</div>
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
.method-list {
  padding: 12px 16px;
}
.method-card {
  background: $card;
  border-radius: $radius;
  padding: 14px;
  margin-bottom: 10px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
}
.method-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 6px;
}
.method-preview {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 8px;
}
.method-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.method-date {
  font-size: 11px;
  color: var(--text-muted);
}
.page-loading {
  padding: 36px 0;
  display: block;
  text-align: center;
}
.detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
}
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.detail-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
}
.detail-content {
  flex: 1;
  overflow-y: auto;
  font-size: 14px;
  color: var(--text);
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>
