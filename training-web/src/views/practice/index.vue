<script setup lang="ts">
import { useRouter } from 'vue-router'
import { PRACTICE_MODULES } from '@/types'

const router = useRouter()

// 7 role-play scenarios (exclude general which is separate)
const scenarioList = PRACTICE_MODULES.filter(m => m.code !== 'general')

const categoryColors: Record<string, string> = {
  '流程': '#0e7490',
  '话术': '#7c3aed',
  '产品': '#059669',
  '技巧': '#d97706',
  '综合': '#dc2626'
}

function goScenario(code: string) {
  router.push(`/practice/agent/${code}`)
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">实战演练</h2>
      <p class="page-subtitle">选择场景，与 AI 对话模拟真实销售情境</p>
    </div>

    <!-- Scenario Grid -->
    <div class="scenario-grid">
      <div
        v-for="scene in scenarioList"
        :key="scene.code"
        class="scenario-card"
        @click="goScenario(scene.code)"
      >
        <div class="card-icon" :style="{ background: categoryColors[scene.category] || 'var(--primary)' }">
          <van-icon :name="scene.icon" size="26" color="#fff" />
        </div>
        <div class="card-body">
          <div class="card-title">{{ scene.title }}</div>
          <div class="card-desc">{{ scene.description }}</div>
        </div>
        <van-tag
          round
          size="medium"
          :color="categoryColors[scene.category] || 'var(--primary)'"
          text-color="#fff"
        >
          {{ scene.category }}
        </van-tag>
      </div>
    </div>

    <!-- Free Practice (General) -->
    <div class="section-divider">
      <span>其他模式</span>
    </div>

    <div class="general-card" @click="goScenario('general')">
      <div class="general-icon">
        <van-icon name="fire-o" size="30" color="var(--danger)" />
      </div>
      <div class="general-info">
        <div class="general-title">自由演练</div>
        <div class="general-desc">AI 教练模式，不扮演顾客，回答你的销售相关问题并提供话术建议</div>
      </div>
      <van-icon name="arrow" size="16" color="var(--text-muted)" />
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

// ── Scenario Grid ───────────────────────────────────────────────────
.scenario-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 12px 16px;
}

.scenario-card {
  background: $card;
  border-radius: $radius;
  padding: 14px 12px 12px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 8px;

  &:active {
    transform: scale(0.96);
    opacity: 0.85;
  }
}

.card-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 3px;
  line-height: 1.3;
}

.card-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

// ── Section Divider ──────────────────────────────────────────────────
.section-divider {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  gap: 10px;
  margin-top: 4px;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }

  span {
    font-size: 12px;
    color: var(--text-muted);
  }
}

// ── General Card ─────────────────────────────────────────────────────
.general-card {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 16px 16px;
  padding: 16px;
  border-radius: $radius;
  background: linear-gradient(135deg, #fef2f2, #fee2e2);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s;
  border: 1px solid rgba(220, 38, 38, 0.12);

  &:active {
    transform: translateX(4px);
    opacity: 0.9;
  }
}

.general-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(220, 38, 38, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.general-info {
  flex: 1;
  min-width: 0;
}

.general-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}

.general-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}
</style>
