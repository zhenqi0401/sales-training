<script setup lang="ts">
import type { SalesScript } from '@/types'
import { useFavoritesStore } from '@/stores/favorites'
import { showToast } from 'vant'

const props = defineProps<{
  script: SalesScript
}>()

const emit = defineEmits<{
  click: [id: number]
}>()

const favoritesStore = useFavoritesStore()

function handleFavorite() {
  favoritesStore.toggleFavorite(props.script)
  showToast(props.script.isFavorite ? '已收藏' : '已取消收藏')
}

function handleCopy(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('已复制到剪贴板')
  }).catch(() => {
    // Fallback for older browsers
    const textarea = document.createElement('textarea')
    textarea.value = text
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    showToast('已复制到剪贴板')
  })
}
</script>

<template>
  <div class="script-box" @click="emit('click', script.id)">
    <div class="script-header">
      <span class="script-title">{{ script.title }}</span>
      <div class="script-actions">
        <van-icon
          :name="script.isFavorite ? 'star' : 'star-o'"
          :color="script.isFavorite ? 'var(--warning)' : 'var(--text-muted)'"
          size="18"
          @click.stop="handleFavorite"
        />
      </div>
    </div>
    <div class="script-summary">{{ script.summary }}</div>
    <div class="script-tags" v-if="script.tags && script.tags.length">
      <van-tag
        v-for="(tag, idx) in script.tags.slice(0, 3)"
        :key="idx"
        plain
        size="small"
        color="var(--primary)"
        style="margin-right: 6px; margin-bottom: 4px;"
      >
        {{ tag }}
      </van-tag>
    </div>
    <div class="script-footer">
      <span class="script-date">{{ script.createdAt?.slice(0, 10) }}</span>
      <van-button
        size="small"
        plain
        type="primary"
        round
        @click.stop="handleCopy(script.content)"
      >
        复制话术
      </van-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.script-box {
  background: $card;
  border-radius: $radius;
  padding: 16px;
  margin: 0 16px 12px;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s;

  &:active {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }
}

.script-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.script-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  flex: 1;
  margin-right: 8px;
}

.script-summary {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.script-tags {
  margin-bottom: 10px;
}

.script-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.script-date {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
