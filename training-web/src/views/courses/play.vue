<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { learningApi } from '@/api/learning'
import { useLearningStore } from '@/stores/learning'
import type { Video } from '@/types'
import { showToast } from 'vant'

const route = useRoute()
const router = useRouter()
const learningStore = useLearningStore()
const videoId = computed(() => Number(route.params.videoId))

const video = ref<Video | null>(null)
const videoRef = ref<HTMLVideoElement | null>(null)
const loading = ref(true)
const playing = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const progress = ref(0)
const videoOrientation = ref<'landscape' | 'portrait' | 'square'>('landscape')

let progressTimer: ReturnType<typeof setInterval> | null = null
let progressSaving = false
let pendingProgressSave = false
let lastSyncedProgress: {
  videoId: number
  watchDuration: number
  progress: number
  completed: boolean
} | null = null

onMounted(async () => {
  try {
    const res = await learningApi.getVideoDetail(videoId.value)
    video.value = res.data
    duration.value = video.value.duration
    updateVideoOrientationFromResolution(video.value.resolution)

    const saved = learningStore.videoProgress[videoId.value]
    if (saved) {
      progress.value = saved.progress
      if (videoRef.value && saved.watchDuration > 0) {
        videoRef.value.currentTime = saved.watchDuration
      }
    }
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  stopProgressTimer()
  void saveProgress({ force: true })
  if (videoRef.value) {
    videoRef.value.pause()
  }
})

function startProgressTimer() {
  stopProgressTimer()
  progressTimer = setInterval(() => {
    if (!video.value) return
    const ct = videoRef.value?.currentTime ?? currentTime.value
    currentTime.value = Math.floor(ct)
    if (duration.value > 0) {
      progress.value = Math.min(100, Math.round((currentTime.value / duration.value) * 100))
    }
    void saveProgress()
  }, 1000)
}

function stopProgressTimer() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

function onVideoPlay() {
  playing.value = true
  startProgressTimer()
}

function onVideoPause() {
  playing.value = false
  stopProgressTimer()
  void saveProgress({ force: true })
}

function onVideoEnded() {
  playing.value = false
  stopProgressTimer()
  completeVideo()
}

function onVideoTimeUpdate() {
  if (!videoRef.value) return
  currentTime.value = Math.floor(videoRef.value.currentTime)
}

function onVideoLoadedMetadata() {
  if (!videoRef.value) return
  duration.value = Math.floor(videoRef.value.duration)
  updateVideoOrientation(videoRef.value.videoWidth, videoRef.value.videoHeight)
  const saved = learningStore.videoProgress[videoId.value]
  if (saved?.watchDuration) {
    videoRef.value.currentTime = saved.watchDuration
  }
}

function updateVideoOrientationFromResolution(resolution?: string) {
  const match = /^(\d+)x(\d+)$/i.exec(resolution || '')
  if (!match) return
  updateVideoOrientation(Number(match[1]), Number(match[2]))
}

function updateVideoOrientation(width: number, height: number) {
  if (!width || !height) return
  if (Math.abs(width - height) <= 2) {
    videoOrientation.value = 'square'
  } else {
    videoOrientation.value = width > height ? 'landscape' : 'portrait'
  }
}

function shouldSyncProgress(completed: boolean) {
  if (!video.value) return false
  if (!lastSyncedProgress) return true
  if (lastSyncedProgress.videoId !== video.value.id) return true
  if (completed && !lastSyncedProgress.completed) return true
  return currentTime.value - lastSyncedProgress.watchDuration >= 5
}

async function saveProgress(options: { force?: boolean } = {}) {
  if (!video.value) return
  const completed = progress.value >= 90
  learningStore.updateVideoProgress(video.value.id, {
    progress: progress.value,
    completed,
    watchDuration: currentTime.value,
  })
  if (!options.force && !shouldSyncProgress(completed)) return
  if (progressSaving) {
    pendingProgressSave = true
    return
  }

  const payload = {
    videoId: video.value.id,
    watchDuration: currentTime.value,
    progress: progress.value,
    completed,
  }

  progressSaving = true
  try {
    await learningApi.updateProgress(payload)
    lastSyncedProgress = payload
  } catch {
    // Local progress is available and will be overwritten after the next successful sync.
  } finally {
    progressSaving = false
    if (pendingProgressSave) {
      pendingProgressSave = false
      void saveProgress({ force: true })
    }
  }
}

async function completeVideo() {
  if (!video.value) return
  playing.value = false
  progress.value = 100
  learningStore.updateVideoProgress(video.value.id, {
    progress: 100,
    completed: true,
    watchDuration: duration.value,
  })
  try {
    await learningApi.updateProgress({
      videoId: video.value.id,
      progress: 100,
      completed: true,
      watchDuration: duration.value,
    })
    lastSyncedProgress = {
      videoId: video.value.id,
      progress: 100,
      completed: true,
      watchDuration: duration.value,
    }
  } catch {
    // Keep the completion state locally if the network is temporarily unavailable.
  }
  showToast('学习完成！')
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
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
      <!-- Video Player -->
      <div class="player-area" :class="`is-${videoOrientation}`">
        <video
          ref="videoRef"
          class="video-element"
          :src="video.url"
          :poster="video.cover"
          playsinline
          controls
          @play="onVideoPlay"
          @pause="onVideoPause"
          @ended="onVideoEnded"
          @timeupdate="onVideoTimeUpdate"
          @loadedmetadata="onVideoLoadedMetadata"
        />
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
          <span class="time-label">{{ formatTime(duration) }}</span>
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
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  aspect-ratio: 16 / 9;
}

.player-area.is-portrait {
  aspect-ratio: 9 / 16;
  max-height: calc(100vh - 46px);
}

.player-area.is-square {
  aspect-ratio: 1 / 1;
}

.video-element {
  width: 100%;
  height: 100%;
  display: block;
  background: #000;
  object-fit: contain;
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
