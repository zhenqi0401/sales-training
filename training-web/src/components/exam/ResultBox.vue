<script setup lang="ts">
import type { ExamRecord } from '@/types'

const props = defineProps<{
  record: ExamRecord
}>()

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}分${s}秒`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<template>
  <div class="result-box" :class="{ passed: record.passed, failed: !record.passed }">
    <div class="result-badge">
      <span v-if="record.passed" class="badge pass">通过</span>
      <span v-else class="badge fail">未通过</span>
    </div>
    <div class="result-score">{{ record.score }}<small>/{{ record.totalScore }}</small></div>
    <div class="result-stats">
      <div class="stat-item">
        <span class="stat-label">正确</span>
        <span class="stat-value correct">{{ record.correctCount }}/{{ record.totalCount }}</span>
      </div>
      <div class="stat-divider" />
      <div class="stat-item">
        <span class="stat-label">用时</span>
        <span class="stat-value time">{{ formatDuration(record.duration) }}</span>
      </div>
      <div class="stat-divider" />
      <div class="stat-item">
        <span class="stat-label">时间</span>
        <span class="stat-value date">{{ formatDate(record.submittedAt) }}</span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.result-box {
  background: $card;
  border-radius: $radius-lg;
  padding: 24px 20px;
  margin: 0 16px;
  text-align: center;
  box-shadow: var(--shadow-sm);

  &.passed {
    border: 2px solid var(--success);
  }

  &.failed {
    border: 2px solid var(--danger);
  }
}

.result-badge {
  margin-bottom: 12px;
}

.badge {
  display: inline-block;
  padding: 4px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;

  &.pass {
    background: var(--success-light);
    color: var(--success);
  }

  &.fail {
    background: #fecaca;
    color: var(--danger);
  }
}

.result-score {
  font-size: 48px;
  font-weight: 800;
  color: var(--text);
  line-height: 1;
  margin-bottom: 20px;

  small {
    font-size: 18px;
    font-weight: 400;
    color: var(--text-muted);
  }
}

.result-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 0 16px;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.stat-value {
  font-size: 14px;
  font-weight: 600;

  &.correct {
    color: var(--success);
  }
  &.time {
    color: var(--primary);
  }
  &.date {
    color: var(--text-secondary);
    font-size: 12px;
  }
}

.stat-divider {
  width: 1px;
  height: 30px;
  background: var(--border);
}
</style>
