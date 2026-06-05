<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { learningApi } from '@/api/learning'
import type { Category } from '@/types'
import { showToast } from 'vant'

const router = useRouter()
const loading = ref(true)
const categories = ref<Category[]>([])

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
  try {
    const res = await learningApi.getCategories()
    categories.value = res.data || []
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">全部课程</h2>
      <p class="page-subtitle">系统学习眼视光销售知识</p>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading">加载中...</van-loading>

    <div v-else class="category-list">
      <div
        v-for="cat in categories"
        :key="cat.id"
        class="category-card"
        @click="router.push(`/courses/list/${cat.id}`)"
      >
        <div class="category-icon" :style="{ background: categoryColors[cat.code] || 'var(--primary)' }">
          <van-icon :name="categoryIcons[cat.code] || 'label-o'" size="28" color="#fff" />
        </div>
        <div class="category-info">
          <div class="category-name">{{ categoryNames[cat.code] || cat.name }}</div>
          <div class="category-desc">{{ cat.description }}</div>
          <div class="category-meta">
            <span class="video-count">{{ cat.videoCount }}个视频</span>
            <span class="completed-count" v-if="cat.completedCount > 0">
              已完成 {{ cat.completedCount }}
            </span>
          </div>
        </div>
        <van-icon name="arrow" size="16" color="var(--text-muted)" />
      </div>
    </div>
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
  padding: 60px 0;
}

.category-list {
  padding: 12px 16px;
}

.category-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: $card;
  border-radius: $radius;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.2s;

  &:active {
    transform: translateX(4px);
  }
}

.category-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.category-info {
  flex: 1;
  min-width: 0;
}

.category-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.category-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.category-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
}

.video-count {
  color: var(--text-muted);
}

.completed-count {
  color: var(--success);
}
</style>
