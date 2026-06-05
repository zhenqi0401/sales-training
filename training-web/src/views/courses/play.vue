<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { learningApi } from '@/api/learning'
import { useLearningStore } from '@/stores/learning'
import type { Video } from '@/types'
import { showToast, showLoadingToast, closeToast } from 'vant'

const route = useRoute()
const router = useRouter()
const learningStore = useLearningStore()
const videoId = computed(() => Number(route.params.videoId))

const video = ref<Video | null>(null)
const loading = ref(true)
const playing = ref(false)
const currentTime = ref(0)
const progress = ref(0)
const fullDuration = ref(0)

// Auto progress tracking
let progressTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    const res = await learningApi.getVideoDetail(videoId.value)
    video.value = res.data
    fullDuration.value = video.value.duration

    // Restore progress
    const saved = learningStore.videoProgress[videoId.value]
    if (saved) {
      progress.value = saved.progress
      currentTime.value = saved.watchDuration
    }
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (progressTimer) {
    clearInterval(progressTimer)
  }
})

function togglePlay() {
  playing.value = !playing.value
  if (playing.value) {
    // Simulate playback progress
    progressTimer = setInterval(() => {
      currentTime.value += 1
      if (fullDuration.value > 0) {
        progress.value = Math.min(100, Math.round((currentTime.value / fullDuration.value) * 100))
      }
      // Track progress every 5 seconds
      if (currentTime.value % 5 === 0 && video.value) {
        saveProgress()
      }
      // Auto-complete at 90%+
      if (progress.value >= 90 && video.value) {
        completeVideo()
      }
    }, 1000)
  } else {
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    if (currentTime.value > 0) {
      saveProgress()
    }
  }
}

async function saveProgress() {
  if (!video.value) return
  learningStore.updateVideoProgress(video.value.id, {
    progress: progress.value,
    completed: progress.value >= 90,
    watchDuration: currentTime.value
  })
}

async function completeVideo() {
  if (!video.value) return
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
  playing.value = false
  progress.value = 100
  learningStore.updateVideoProgress(video.value.id, {
    progress: 100,
    completed: true,
    watchDuration: currentTime.value
  })
  showToast('学习完成！')
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}
</script>

<template>
  <div class="play-page page-no-tabbar">
    <van-nav-bar
      title="视频学习"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else-if="video">
      <!-- Video Player Area -->
      <div class="player-area" @click="togglePlay">
        <div class="player-cover" v-if="!playing">
          <van-image :src="video.cover" fit="cover" width="100%" height="100%" />
          <div class="play-overlay">
            <van-icon name="play-circle" size="60" color="#fff" />
          </div>
          <div class="player-info">
            <span class="duration">{{ formatTime(video.duration) }}</span>
          </div>
        </div>
        <div v-else class="player-simulating">
          <div class="simulate-bar">
            <van-icon name="music" size="40" color="var(--primary)" />
            <p>视频播放中...</p>
            <div class="simulate-progress">
              <div class="progress-fill" :style="{ width: progress + '%' }" />
            </div>
          </div>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="progress-section">
        <div class="progress-row">
          <span class="time-label">{{ formatTime(currentTime) }}</span>
          <van-progress
            :percentage="progress"
            :stroke-width="6"
            color="linear-gradient(90deg, var(--primary), var(--success))"
            track-color="#e2e8f0"
            :show-pivot="false"
          />
          <span class="time-label">{{ formatTime(video.duration) }}</span>
        </div>
      </div>

      <!-- Video Info -->
      <div class="video-info section-card">
        <h3 class="video-title">{{ video.title }}</h3>
        <div class="video-meta">
          <span class="meta-item">
            <van-icon name="manager-o" size="14" />
            {{ video.讲师 || '讲师' }}
          </span>
          <span class="meta-item">
            <van-icon name="clock-o" size="14" />
            {{ formatTime(video.duration) }}
          </span>
          <span class="meta-item" :class="{ completed: video.completed }">
            <van-icon :name="video.completed ? 'checked' : 'underway-o'" size="14" />
            {{ video.completed ? '已完成' : '学习中' }}
          </span>
        </div>
        <div class="video-desc" v-if="video.description">
          <p>{{ video.description }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page-loading {
  padding: 60px 0;
}

.player-area {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  overflow: hidden;
}

.player-cover {
  position: relative;
  width: 100%;
  height: 100%;
}

.play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
}

.player-info {
  position: absolute;
  bottom: 10px;
  right: 10px;
}

.duration {
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.player-simulating {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
}

.simulate-bar {
  text-align: center;
  color: var(--text-secondary);
  width: 80%;
}

.simulate-bar p {
  margin: 8px 0;
  font-size: 14px;
}

.simulate-progress {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--success));
  transition: width 0.3s;
}

.progress-section {
  padding: 12px 16px;
  background: $card;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-label {
  font-size: 12px;
  color: var(--text-muted);
  min-width: 36px;
  text-align: center;
}

.video-info {
  margin-top: 0;
}

.video-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}

.video-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-secondary);

  &.completed {
    color: var(--success);
  }
}

.video-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.7;
}
</style>
