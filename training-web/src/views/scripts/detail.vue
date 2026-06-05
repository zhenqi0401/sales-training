<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { scriptsApi } from '@/api/scripts'
import { useFavoritesStore } from '@/stores/favorites'
import type { SalesScript } from '@/types'

const route = useRoute()
const router = useRouter()
const favoritesStore = useFavoritesStore()

const scriptId = computed(() => Number(route.params.id))
const script = ref<SalesScript | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await scriptsApi.getScriptDetail(scriptId.value)
    script.value = res.data
    // Sync favorite state
    if (script.value) {
      script.value.isFavorite = favoritesStore.isFavorite(script.value.id)
    }
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

function toggleFavorite() {
  if (!script.value) return
  favoritesStore.toggleFavorite(script.value)
  showToast(script.value.isFavorite ? '已收藏' : '已取消收藏')
}

function copyContent() {
  if (!script.value) return
  navigator.clipboard.writeText(script.value.content).then(() => {
    showToast('已复制到剪贴板')
  }).catch(() => {
    const textarea = document.createElement('textarea')
    textarea.value = script.value!.content
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    showToast('已复制到剪贴板')
  })
}
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar
      title="话术详情"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    >
      <template #right>
        <van-icon
          :name="script?.isFavorite ? 'star' : 'star-o'"
          :color="script?.isFavorite ? 'var(--warning)' : ''"
          size="20"
          @click="toggleFavorite"
        />
      </template>
    </van-nav-bar>

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else-if="script">
      <!-- Script Header -->
      <div class="script-header">
        <h2 class="script-title">{{ script.title }}</h2>
        <div class="script-tags" v-if="script.tags && script.tags.length">
          <van-tag
            v-for="(tag, idx) in script.tags"
            :key="idx"
            plain
            color="var(--primary)"
            style="margin-right: 6px;"
          >
            {{ tag }}
          </van-tag>
        </div>
        <p class="script-summary">{{ script.summary }}</p>
      </div>

      <!-- Script Content -->
      <div class="script-content section-card">
        <div class="content-label">
          <van-icon name="chat-o" size="16" color="var(--primary)" />
          <span>话术内容</span>
        </div>
        <div class="content-text">{{ script.content }}</div>
      </div>

      <!-- Action Bar -->
      <div class="action-bar">
        <van-button
          round
          block
          color="linear-gradient(135deg, var(--primary), var(--primary-dark))"
          icon="copy-o"
          @click="copyContent"
        >
          复制话术
        </van-button>
        <van-button
          round
          plain
          type="primary"
          :icon="script.isFavorite ? 'star' : 'star-o'"
          @click="toggleFavorite"
          style="margin-left: 12px; flex-shrink: 0;"
        >
          {{ script.isFavorite ? '已收藏' : '收藏' }}
        </van-button>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page-loading {
  padding: 60px 0;
}

.script-header {
  padding: 16px;
  background: $card;
  margin-bottom: 4px;
}

.script-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 10px;
}

.script-tags {
  margin-bottom: 10px;
}

.script-summary {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.script-content {
  margin-top: 0;
}

.content-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}

.content-text {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text);
  white-space: pre-wrap;
}

.action-bar {
  display: flex;
  padding: 16px;
  background: $card;
  position: sticky;
  bottom: 0;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);

  .van-button {
    flex: 1;
  }
}
</style>
