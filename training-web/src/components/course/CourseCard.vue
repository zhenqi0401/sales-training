<script setup lang="ts">
import type { Video } from '@/types'

const props = defineProps<{
  video: Video
}>()

const emit = defineEmits<{
  click: [videoId: number]
}>()

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m >= 60) {
    const h = Math.floor(m / 60)
    return `${h}:${String(m % 60).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${m}:${String(s).padStart(2, '0')}`
}
</script>

<template>
  <div class="course-card" @click="emit('click', video.id)">
    <div class="card-cover">
      <van-image
        :src="video.cover"
        fit="cover"
        class="cover-img"
        loading-icon="photo-o"
      />
      <span class="card-duration">{{ formatDuration(video.duration) }}</span>
      <div v-if="video.completed" class="card-status completed">
        <van-icon name="success" size="14" />
      </div>
      <div v-else-if="video.progress > 0" class="card-status progress-tag">
        {{ video.progress }}%
      </div>
    </div>
    <div class="card-info">
      <div class="card-title van-multi-ellipsis--l2">{{ video.title }}</div>
      <div class="card-meta">
        <span class="card-author">{{ video.讲师 || '讲师' }}</span>
        <span class="card-progress">
          <van-progress
            :percentage="video.progress"
            :stroke-width="4"
            color="linear-gradient(90deg, var(--primary), var(--success))"
            :show-pivot="false"
            track-color="#e8edf0"
          />
        </span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.course-card {
  background: $card;
  border-radius: $radius;
  overflow: hidden;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  transition: transform 0.2s;
  &:active {
    transform: scale(0.98);
  }
}

.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;

  .cover-img {
    width: 100%;
    height: 100%;
  }

  .card-duration {
    position: absolute;
    bottom: 6px;
    right: 6px;
    background: rgba(0, 0, 0, 0.6);
    color: #fff;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .card-status {
    position: absolute;
    top: 6px;
    right: 6px;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    line-height: 1;

    &.completed {
      background: var(--success);
      color: #fff;
      display: flex;
      align-items: center;
      gap: 2px;
    }

    &.progress-tag {
      background: rgba(14, 116, 144, 0.85);
      color: #fff;
    }
  }
}

.card-info {
  padding: 10px 12px 12px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.4;
  margin-bottom: 8px;
  min-height: 20px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-author {
  font-size: 12px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.card-progress {
  flex: 1;
}
</style>
