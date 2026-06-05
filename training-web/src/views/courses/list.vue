<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { learningApi } from '@/api/learning'
import type { Video } from '@/types'
import CourseCard from '@/components/course/CourseCard.vue'
import { showToast } from 'vant'

const route = useRoute()
const router = useRouter()
const categoryId = computed(() => Number(route.params.categoryId))

const loading = ref(true)
const videos = ref<Video[]>([])

const categoryNames: Record<number, string> = {
  1: '青控', 2: '斜弱视', 3: '角塑', 4: '眼镜', 5: '周边产品', 6: '功能性眼镜', 7: '企业文化'
}

const categoryName = computed(() => categoryNames[categoryId.value] || '课程')

onMounted(async () => {
  try {
    const res = await learningApi.getVideosByCategory(categoryId.value)
    videos.value = res.data || []
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

function goPlay(videoId: number) {
  router.push(`/courses/play/${videoId}`)
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

    <EmptyState v-else-if="videos.length === 0" description="暂无课程" />

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
</style>
