<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showToast } from 'vant'
import { salesApi } from '@/api/sales'

const loading = ref(true)
const stats = ref({ totalSales: 0, totalAudioFiles: 0, totalMethodologies: 0 })

async function loadDashboard() {
  loading.value = true
  try {
    const res = await salesApi.getDashboard()
    stats.value = res.data || stats.value
  } catch {
    showToast('看板数据加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">销售看板</h2>
      <p class="page-subtitle">销售团队整体数据概览</p>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading">加载中...</van-loading>

    <template v-else>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-num">{{ stats.totalSales }}</div>
          <div class="stat-label">销售人员</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ stats.totalAudioFiles }}</div>
          <div class="stat-label">语音文件</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ stats.totalMethodologies }}</div>
          <div class="stat-label">方法论</div>
        </div>
      </div>

      <div class="section-card">
        <div class="section-title">快速入口</div>
        <van-cell title="销售方法论" icon="medal-o" is-link to="/sales/methodology" />
      </div>
    </template>
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
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 16px;
}
.stat-card {
  background: $card;
  border-radius: $radius;
  padding: 16px 8px;
  text-align: center;
  box-shadow: var(--shadow-sm);
}
.stat-num {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary);
}
.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}
.section-card {
  margin: 0 16px 16px;
  background: $card;
  border-radius: $radius;
  padding: 16px;
  box-shadow: var(--shadow-sm);
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}
.page-loading {
  padding: 36px 0;
  display: block;
  text-align: center;
}
</style>
