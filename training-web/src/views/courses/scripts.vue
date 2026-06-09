<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { learningApi } from '@/api/learning'
import { useFavoritesStore } from '@/stores/favorites'
import { showToast } from 'vant'

const router = useRouter()
const route = useRoute()
const favoritesStore = useFavoritesStore()

const loading = ref(false)
const scripts = ref<any[]>([])
const categories = ref<{ code: string; name: string; count: number }[]>([])
const activeCategory = ref<string | undefined>(undefined)
const favoriteOnly = computed(() => route.query.favorites === '1')

const categoryLabels: Record<string, string> = {
  drucker: '德鲁克',
  girard: '乔·吉拉德',
  hopkins: '霍普金斯',
  gitomer: '吉特默',
  trout: '特劳特',
  burnett: '李奥·贝纳',
  masters: '大师通识',
  price: '价格敏感',
  delay: '拖延犹豫',
  awareness: '认知不足',
  brand: '品牌偏好',
  info_bias: '信息偏差',
  trust: '信任/效果疑虑',
  competitor: '竞品对比',
  execution: '执行难度',
  safety: '安全担忧',
  knowledge: '常识科普',
  online: '网络热议',
  fang_kong: '防控镜片',
  jiao_su: '角塑异议',
  opening: '开场白',
  product: '产品介绍',
  objection: '异议处理',
  closing: '促单成交',
  service: '售后服务',
  general: '通用话术',
  prototype_card: '大师通识',
  prototype_script: '通用话术',
}

const activeCategoryName = computed(() => {
  if (!activeCategory.value) return '全部'
  return categoryLabels[activeCategory.value] || activeCategory.value
})

onMounted(async () => {
  await loadScripts()
})

watch(
  () => route.query.favorites,
  async () => {
    await loadScripts()
  }
)

async function loadScripts(category?: string) {
  loading.value = true
  activeCategory.value = category
  try {
    const res = await learningApi.getScripts(category, 1, 200, favoriteOnly.value)
    const data = res.data
    scripts.value = (data?.items || []).map((s: any) => ({
      ...s,
      summary: s.theory || '',
      isFavorite: s.isFavorite || favoritesStore.isFavorite(s.id),
    }))
    if (favoriteOnly.value) {
      favoritesStore.setFavorites(scripts.value.map((script: any) => ({ ...script, isFavorite: true })) as any)
    }
    if (data?.categories) {
      categories.value = data.categories
    }
  } catch {
    scripts.value = []
  } finally {
    loading.value = false
  }
}

async function toggleFavorite(script: any) {
  try {
    await learningApi.toggleScriptFavorite(script.id, script.isFavorite)
    const nextFavorite = !script.isFavorite
    script.isFavorite = nextFavorite
    const favoriteScript = {
      id: script.id,
      categoryId: 0,
      title: script.title,
      content: script.content,
      summary: script.theory,
      tags: script.tags || [],
      isFavorite: nextFavorite,
      createdAt: script.createdAt || '',
    } as any
    if (nextFavorite) {
      favoritesStore.addFavorite(favoriteScript)
    } else {
      favoritesStore.removeFavorite(script.id)
      if (favoriteOnly.value) {
        scripts.value = scripts.value.filter((item) => item.id !== script.id)
        categories.value = categories.value
          .map((cat) => cat.code === script.category ? { ...cat, count: Math.max(cat.count - 1, 0) } : cat)
          .filter((cat) => cat.count > 0)
      }
    }
    showToast(script.isFavorite ? '已收藏' : '已取消收藏')
  } catch {
    showToast('操作失败')
  }
}

function copyContent(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('已复制到剪贴板')
  }).catch(() => {
    const textarea = document.createElement('textarea')
    textarea.value = text
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    showToast('已复制到剪贴板')
  })
}

function goDetail(id: number) {
  router.push(`/courses/script/${id}`)
}

function expandScript(script: any) {
  script._expanded = !script._expanded
}

</script>

<template>
  <div class="scripts-page">
    <van-nav-bar
      v-if="favoriteOnly"
      title="收藏话术"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <!-- Category filter chips -->
    <div class="category-tabs" v-if="categories.length">
      <span
        class="filter-chip"
        :class="{ active: !activeCategory }"
        @click="loadScripts()"
      >全部</span>
      <span
        v-for="cat in categories"
        :key="cat.code"
        class="filter-chip"
        :class="{ active: activeCategory === cat.code }"
        @click="loadScripts(cat.code)"
      >
        {{ cat.name }} ({{ cat.count }})
      </span>
    </div>

    <van-loading v-if="loading" size="20" class="page-loading" />

    <template v-else-if="scripts.length">
      <div
        v-for="script in scripts"
        :key="script.id"
        class="script-card"
        :class="{ expanded: script._expanded }"
      >
        <!-- Card header -->
        <div class="script-card-header" @click="expandScript(script)">
          <div class="card-title-row">
            <span class="card-title">{{ script.title }}</span>
            <span class="card-category-tag">{{ categoryLabels[script.category] || script.category }}</span>
          </div>

          <!-- Theory section -->
          <div class="theory-block" v-if="script.theory">
            <span class="theory-label">理论说明</span>
            <p class="theory-text">{{ script.theory }}</p>
          </div>

          <van-icon
            :name="script._expanded ? 'arrow-up' : 'arrow-down'"
            size="14"
            color="var(--text-muted)"
            class="expand-icon"
          />
        </div>

        <!-- Expandable content area -->
        <div class="script-card-body" v-show="script._expanded">
          <div class="content-section">
            <div class="content-label">
              <van-icon name="chat-o" size="14" color="var(--primary)" />
              实战话术
            </div>
            <pre class="content-text">{{ script.content }}</pre>
          </div>

          <div class="card-actions">
            <van-button
              size="small"
              round
              plain
              type="primary"
              icon="copy-o"
              @click.stop="copyContent(script.content)"
            >
              一键复制
            </van-button>
            <van-button
              size="small"
              round
              :plain="!script.isFavorite"
              :type="script.isFavorite ? 'warning' : 'default'"
              :icon="script.isFavorite ? 'star' : 'star-o'"
              @click.stop="toggleFavorite(script)"
            >
              {{ script.isFavorite ? '已收藏' : '收藏' }}
            </van-button>
          </div>
        </div>
      </div>
    </template>

    <EmptyState v-else :description="favoriteOnly ? '暂无收藏话术' : '暂无话术内容'" />
  </div>
</template>

<style lang="scss" scoped>
.category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
}

.filter-chip {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 999px;
  background: #f1f5f9;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;

  &.active {
    background: var(--primary);
    color: #fff;
    font-weight: 600;
  }

  &:active {
    transform: scale(0.96);
  }
}

.page-loading {
  padding: 40px 0;
}

.script-card {
  background: $card;
  border-radius: $radius;
  margin: 0 16px 12px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);

  &.expanded {
    box-shadow: var(--shadow-md);
  }
}

.script-card-header {
  padding: 14px 16px;
  cursor: pointer;
  position: relative;

  &:active {
    background: #f8fafc;
  }
}

.card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  flex: 1;
}

.card-category-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #e6f6f4;
  color: var(--primary);
  white-space: nowrap;
}

.scene-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.scene-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
}

.theory-block {
  background: #f8fafc;
  border-radius: 6px;
  padding: 10px 12px;
  border-left: 3px solid var(--primary);
}

.theory-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--primary);
  margin-bottom: 4px;
  display: block;
}

.theory-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}

.expand-icon {
  position: absolute;
  top: 14px;
  right: 16px;
}

.script-card-body {
  border-top: 1px solid var(--border-light);
  padding: 14px 16px;
}

.content-section {
  margin-bottom: 14px;
}

.content-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 10px;
}

.content-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  margin: 0;
  background: #fafbfc;
  border-radius: 6px;
  padding: 12px;
}

.card-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
</style>
