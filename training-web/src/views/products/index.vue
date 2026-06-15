<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const searchValue = ref('')

const categories = [
  { id: 1, name: '镜架', icon: 'goods-collect-o', productCount: 24, color: '#0e7490' },
  { id: 2, name: '镜片', icon: 'more-o', productCount: 36, color: '#7c3aed' },
  { id: 3, name: '青控产品', icon: 'eye-o', productCount: 12, color: '#059669' },
  { id: 4, name: '角塑产品', icon: 'aim', productCount: 8, color: '#0891b2' },
  { id: 5, name: '太阳镜', icon: 'gem-o', productCount: 18, color: '#d97706' },
  { id: 6, name: '隐形眼镜', icon: 'underway-o', productCount: 15, color: '#dc2626' },
  { id: 7, name: '护眼产品', icon: 'shield-o', productCount: 10, color: '#4f46e5' },
  { id: 8, name: '仪器设备', icon: 'scan', productCount: 7, color: '#0891b2' }
]

function goCategory(id: number) {
  router.push(`/products/${id}`)
}

function onSearch(val: string) {
  if (!val.trim()) return
  router.push(`/products?search=${encodeURIComponent(val)}`)
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">产品知识</h2>
      <p class="page-subtitle">眼视光产品知识库</p>
    </div>

    <div class="search-bar">
      <van-search
        v-model="searchValue"
        shape="round"
        placeholder="搜索产品..."
        @search="onSearch"
      />
    </div>

    <div class="product-grid">
      <div
        v-for="cat in categories"
        :key="cat.id"
        class="product-card"
        @click="goCategory(cat.id)"
      >
        <div class="card-bg" :style="{ background: cat.color }">
          <div class="card-icon">
            <van-icon :name="cat.icon" size="32" color="#fff" />
          </div>
        </div>
        <div class="card-info">
          <span class="card-name">{{ cat.name }}</span>
          <span class="card-count">{{ cat.productCount }}个产品</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-header {
  padding: 16px 16px 0;
  background: $card;
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

.search-bar {
  padding: 0 8px;
}

.product-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 12px 16px;
}

.product-card {
  background: $card;
  border-radius: $radius;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.2s;

  &:active {
    transform: scale(0.97);
  }
}

.card-bg {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-info {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.card-count {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
