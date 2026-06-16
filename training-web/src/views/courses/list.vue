<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { learningApi } from '@/api/learning'
import type { Video } from '@/types'
import CourseCard from '@/components/course/CourseCard.vue'
import { showToast } from 'vant'

const route = useRoute()
const router = useRouter()
const categoryId = computed(() => Number(route.params.categoryId))

const loading = ref(true)
const categoryName = ref('')
const children = ref<Array<{ id: number; name: string; code: string; icon: string; description: string; videoCount: number; sort: number }>>([])
const videos = ref<Video[]>([])

const hasChildren = computed(() => children.value.length > 0)

onMounted(() => {
  loadData()
})

watch(categoryId, () => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const res = await learningApi.getVideosByCategory(categoryId.value)
    const data = res.data
    if (data) {
      categoryName.value = data.category?.name || '课程'
      children.value = data.children || []
      videos.value = data.videos || []
    }
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

function goPlay(videoId: number) {
  router.push(`/courses/play/${videoId}`)
}

function goChildren(catId: number) {
  router.push(`/courses/list/${catId}`)
}
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar
      :title="categoryName"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <!-- Sub-category folders -->
    <div v-else-if="hasChildren" class="children-list">
      <div
        v-for="child in children"
        :key="child.id"
        class="child-card"
        @click="goChildren(child.id)"
      >
        <div class="child-info">
          <div class="child-name">{{ child.name }}</div>
          <div class="child-desc" v-if="child.description">{{ child.description }}</div>
        </div>
        <div class="child-right">
          <span class="child-count">{{ child.videoCount }}个视频</span>
          <van-icon name="arrow" size="16" color="var(--text-muted)" />
        </div>
      </div>
    </div>

    <EmptyState v-else-if="videos.length === 0" description="暂无课程" />

    <!-- Video list -->
    <div v-else class="video-list">
      <CourseCard
        v-for="video in videos"
        :key="video.id"
        :video="video"
        @click="goPlay"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-loading {
  padding: 60px 0;
}

.video-list {
  padding: 12px 16px;
}

.children-list {
  padding: 12px 16px;
}

.child-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  margin-bottom: 10px;
  background: $card;
  border-radius: $radius;
  cursor: pointer;

  &:active {
    background: var(--bg-secondary, #f5f7fa);
  }
}

.child-info {
  flex: 1;
}

.child-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.child-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

.child-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.child-count {
  font-size: 13px;
  color: var(--primary);
}
</style>
