<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { learningApi } from '@/api/learning'
import { useFavoritesStore } from '@/stores/favorites'
import { showToast } from 'vant'

const route = useRoute()
const router = useRouter()
const favoritesStore = useFavoritesStore()

const scriptId = computed(() => Number(route.params.scriptId))
const script = ref<any>(null)
const loading = ref(true)

const categoryLabels: Record<string, string> = {
  drucker: '德鲁克', girard: '乔·吉拉德', hopkins: '霍普金斯',
  gitomer: '吉特默', trout: '特劳特', burnett: '李奥·贝纳',
  masters: '大师通识',
  price: '价格敏感', delay: '拖延犹豫', awareness: '认知不足',
  brand: '品牌偏好', info_bias: '信息偏差', trust: '信任/效果疑虑',
  competitor: '竞品对比', execution: '执行难度', safety: '安全担忧',
  knowledge: '常识科普', online: '网络热议',
  fang_kong: '防控镜片', jiao_su: '角塑异议',
  opening: '开场白', product: '产品介绍', objection: '异议处理',
  closing: '促单成交', service: '售后服务', general: '通用话术',
  prototype_card: '大师通识', prototype_script: '通用话术',
}

onMounted(async () => {
  try {
    const res = await learningApi.getScriptDetail(scriptId.value)
    script.value = {
      ...res.data,
      isFavorite: res.data?.isFavorite || favoritesStore.isFavorite(scriptId.value),
    }
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

async function toggleFavorite() {
  if (!script.value) return
  try {
    await learningApi.toggleScriptFavorite(script.value.id, script.value.isFavorite)
    const nextFavorite = !script.value.isFavorite
    script.value.isFavorite = nextFavorite
    const favoriteScript = {
      id: script.value.id,
      categoryId: 0,
      title: script.value.title,
      content: script.value.content,
      summary: script.value.theory,
      tags: script.value.tags || [],
      isFavorite: nextFavorite,
      createdAt: script.value.createdAt || '',
    } as any
    if (nextFavorite) {
      favoritesStore.addFavorite(favoriteScript)
    } else {
      favoritesStore.removeFavorite(script.value.id)
    }
    showToast(script.value.isFavorite ? '已收藏' : '已取消收藏')
  } catch {
    showToast('操作失败')
  }
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
      <!-- Header -->
      <div class="detail-header">
        <div class="header-row">
          <h2 class="detail-title">{{ script.title }}</h2>
          <span class="category-tag">{{ categoryLabels[script.category] || script.category }}</span>
        </div>

      </div>

      <!-- Theory -->
      <div class="section-card" v-if="script.theory">
        <div class="section-label">
          <van-icon name="info-o" size="16" color="var(--primary)" />
          理论说明
        </div>
        <p class="section-text">{{ script.theory }}</p>
      </div>

      <!-- Script Content -->
      <div class="section-card">
        <div class="section-label">
          <van-icon name="chat-o" size="16" color="var(--primary)" />
          实战话术
        </div>
        <pre class="script-content">{{ script.content }}</pre>
      </div>

      <!-- Action Bar -->
      <div class="detail-actions">
        <van-button
          round
          block
          color="linear-gradient(135deg, var(--primary), var(--primary-dark))"
          icon="description-o"
          @click="copyContent"
        >
          一键复制
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

.detail-header {
  padding: 16px;
  background: $card;
}

.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.detail-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}

.category-tag {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 6px;
  background: #e6f6f4;
  color: var(--primary);
  white-space: nowrap;
  font-weight: 600;
}

.section-card {
  margin: 8px 16px;
  background: $card;
  border-radius: $radius;
  padding: 16px;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}

.section-text {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0;
}

.script-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  margin: 0;
  background: #f8fafc;
  border-radius: 8px;
  padding: 14px;
  border-left: 3px solid var(--primary);
}

.detail-actions {
  display: flex;
  padding: 16px;
  background: $card;
  position: sticky;
  bottom: 0;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);

  .van-button--block {
    flex: 1;
  }
}
</style>
