<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const practiceModules = [
  { id: 1, code: 'reception', title: '接待流程演练', description: '标准接待流程七步法', icon: 'service-o', category: '流程' },
  { id: 2, code: 'question', title: '问诊话术演练', description: '专业问诊技巧与话术', icon: 'chat-o', category: '话术' },
  { id: 3, code: 'product', title: '产品介绍演练', description: '产品卖点讲解练习', icon: 'label-o', category: '产品' },
  { id: 4, code: 'objection', title: '异议处理演练', description: '常见顾客异议应对', icon: 'warning-o', category: '技巧' },
  { id: 5, code: 'closing', title: '成交技巧演练', description: '促单成交技巧练习', icon: 'gold-coin-o', category: '技巧' },
  { id: 6, code: 'fitting', title: '验光配镜演练', description: '验光配镜流程模拟', icon: 'medical-o', category: '流程' },
  { id: 7, code: 'aftercare', title: '售后服务演练', description: '售后回访与维护', icon: 'smile-o', category: '流程' }
]

const moduleColors: Record<string, string> = {
  flow: '#0e7490',
  talk: '#7c3aed',
  product: '#059669',
  skill: '#d97706'
}

const categoryColors: Record<string, string> = {
  '流程': '#0e7490',
  '话术': '#7c3aed',
  '产品': '#059669',
  '技巧': '#d97706'
}

function goModule(moduleId: number) {
  router.push(`/practice/module/${moduleId}`)
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">实战演练</h2>
      <p class="page-subtitle">通过情景模拟提升实战能力</p>
    </div>

    <div class="module-list">
      <div
        v-for="(mod, idx) in practiceModules"
        :key="mod.id"
        class="module-card"
        @click="goModule(mod.id)"
      >
        <div class="module-index">{{ String(idx + 1).padStart(2, '0') }}</div>
        <div class="module-icon" :style="{ background: categoryColors[mod.category] || 'var(--primary)' }">
          <van-icon :name="mod.icon" size="24" color="#fff" />
        </div>
        <div class="module-info">
          <div class="module-title">{{ mod.title }}</div>
          <div class="module-desc">{{ mod.description }}</div>
        </div>
        <van-tag round :color="categoryColors[mod.category]" size="medium">{{ mod.category }}</van-tag>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-header {
  padding: 16px 16px 8px;
  background: $card;
  margin-bottom: 4px;
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

.module-list {
  padding: 12px 16px;
}

.module-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: $card;
  border-radius: $radius;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.2s;
  position: relative;

  &:active {
    transform: translateX(4px);
  }
}

.module-index {
  position: absolute;
  right: 16px;
  bottom: 8px;
  font-size: 32px;
  font-weight: 800;
  color: var(--border);
  line-height: 1;
}

.module-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.module-info {
  flex: 1;
  min-width: 0;
  position: relative;
  z-index: 1;
}

.module-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.module-desc {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
