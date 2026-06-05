import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Category, Video } from '@/types'

export const useLearningStore = defineStore(
  'learning',
  () => {
    // State
    const categories = ref<Category[]>([])
    const currentCategoryId = ref<number | null>(null)
    const videoProgress = ref<Record<number, { progress: number; completed: boolean; watchDuration: number }>>({})
    const recentlyWatched = ref<Video[]>([])

    // Getters
    const currentCategory = computed(() =>
      categories.value.find((c) => c.id === currentCategoryId.value) ?? null
    )

    const totalCompletedVideos = computed(() =>
      Object.values(videoProgress.value).filter((v) => v.completed).length
    )

    const overallProgress = computed(() => {
      const total = Object.keys(videoProgress.value).length
      if (total === 0) return 0
      const completed = Object.values(videoProgress.value).filter((v) => v.completed).length
      return Math.round((completed / total) * 100)
    })

    // Actions
    function setCategories(list: Category[]) {
      categories.value = list
    }

    function updateVideoProgress(videoId: number, data: { progress: number; completed: boolean; watchDuration: number }) {
      videoProgress.value[videoId] = data
    }

    function addRecentlyWatched(video: Video) {
      const exists = recentlyWatched.value.findIndex((v) => v.id === video.id)
      if (exists !== -1) {
        recentlyWatched.value.splice(exists, 1)
      }
      recentlyWatched.value.unshift(video)
      if (recentlyWatched.value.length > 20) {
        recentlyWatched.value.pop()
      }
    }

    return {
      categories,
      currentCategoryId,
      videoProgress,
      recentlyWatched,
      currentCategory,
      totalCompletedVideos,
      overallProgress,
      setCategories,
      updateVideoProgress,
      addRecentlyWatched
    }
  },
  {
    persist: {
      key: 'learning-store',
      storage: localStorage,
      paths: ['videoProgress', 'recentlyWatched']
    }
  }
)
