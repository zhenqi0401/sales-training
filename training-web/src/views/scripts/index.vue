<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { scriptsApi } from '@/api/scripts'
import type { ScriptCategory, SalesScript } from '@/types'
import ScriptBox from '@/components/script/ScriptBox.vue'
import { showToast } from 'vant'

const router = useRouter()
const loading = ref(true)
const categories = ref<ScriptCategory[]>([])
const selectedCategory = ref<number | null>(null)
const scripts = ref<SalesScript[]>([])
const searchValue = ref('')

// Master theory categories for the tabs
const masterTheories = [
  { id: 1, name: '接待问诊', masterTheory: '接待', description: '接待问诊话术' },
  { id: 2, name: '产品介绍', masterTheory: '产品介绍', description: '产品介绍话术' },
  { id: 3, name: '异议处理', masterTheory: '异议处理', description: '异议处理话术' },
  { id: 4, name: '价格谈判', masterTheory: '价格谈判', description: '价格谈判话术' },
  { id: 5, name: '促单成交', masterTheory: '促单成交', description: '促单成交话术' },
  { id: 6, name: '售后服务', masterTheory: '售后服务', description: '售后回访话术' }
]

onMounted(async () => {
  try {
    const res = await scriptsApi.getCategories()
    categories.value = res.data || masterTheories
  } catch {
    categories.value = masterTheories
  } finally {
    loading.value = false
  }
})

async function loadScripts(categoryId: number) {
  selectedCategory.value = categoryId
  loading.value = true
  try {
    const res = await scriptsApi.getScriptsByCategory(categoryId)
    scripts.value = res.data || []
  } catch {
    scripts.value = []
  } finally {
    loading.value = false
  }
}

function goDetail(id: number) {
  router.push(`/scripts/${id}`)
}

function onSearch(val: string) {
  if (!val.trim()) return
  router.push(`/scripts?search=${encodeURIComponent(val)}`)
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">销售话术库</h2>
      <p class="page-subtitle">基于大师理论的专业销售话术</p>
    </div>

    <!-- Search -->
    <div class="search-bar">
      <van-search
        v-model="searchValue"
        shape="round"
        placeholder="搜索话术..."
        @search="onSearch"
      />
    </div>

    <!-- Master Theory Tabs -->
    <div class="theory-tabs">
      <div
        v-for="(theory, idx) in masterTheories"
        :key="theory.id"
        class="theory-tab"
        :class="{ active: selectedCategory === theory.id }"
        @click="loadScripts(theory.id)"
      >
        <span class="tab-name">{{ theory.name }}</span>
        <span class="tab-desc">{{ theory.description }}</span>
      </div>
    </div>

    <!-- Script List -->
    <div class="scripts-section">
      <div v-if="scripts.length === 0 && !loading" class="empty-hint">
        <EmptyState description="暂无话术数据" />
      </div>

      <template v-else>
        <ScriptBox
          v-for="script in scripts"
          :key="script.id"
          :script="script"
          @click="goDetail"
        />
      </template>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-header {
  padding: 16px 16px 0;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}

.search-bar {
  padding: 0 8px;
}

.theory-tabs {
  display: flex;
  overflow-x: auto;
  gap: 10px;
  padding: 8px 16px 12px;
  white-space: nowrap;
  -webkit-overflow-scrolling: touch;

  &::-webkit-scrollbar {
    display: none;
  }
}

.theory-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 18px;
  background: $card;
  border: 1.5px solid var(--border);
  border-radius: $radius;
  min-width: 80px;
  cursor: pointer;
  transition: all 0.2s;

  &:active {
    transform: scale(0.96);
  }

  &.active {
    border-color: var(--primary);
    background: linear-gradient(135deg, var(--primary), var(--primary-dark));
    color: #fff;
    box-shadow: 0 4px 12px rgba(14, 116, 144, 0.3);
  }
}

.tab-name {
  font-size: 14px;
  font-weight: 600;
}

.tab-desc {
  font-size: 10px;
  opacity: 0.7;
}

.scripts-section {
  padding: 4px 0 16px;
}

.empty-hint {
  padding: 40px 0;
}
</style>
