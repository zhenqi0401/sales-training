<script setup lang="ts">
import type { Question, QuestionOption } from '@/types'

const props = defineProps<{
  question: Question
  index: number
  selected: string | string[]
}>()

const emit = defineEmits<{
  select: [value: string | string[]]
}>()

function isSelected(option: QuestionOption): boolean {
  if (Array.isArray(props.selected)) {
    return props.selected.includes(option.value)
  }
  return props.selected === option.value
}

function onSelect(option: QuestionOption) {
  if (props.question.type === 'multi') {
    const current = Array.isArray(props.selected) ? [...props.selected] : []
    const idx = current.indexOf(option.value)
    if (idx !== -1) {
      current.splice(idx, 1)
    } else {
      current.push(option.value)
    }
    emit('select', current)
  } else {
    emit('select', option.value)
  }
}

const typeLabel: Record<string, string> = {
  single: '单选题',
  multi: '多选题',
  judge: '判断题'
}
</script>

<template>
  <div class="question-card">
    <div class="question-header">
      <span class="question-number">{{ index + 1 }}.</span>
      <span class="question-type">{{ typeLabel[question.type] || '' }}</span>
      <span class="question-score">{{ question.score }}分</span>
    </div>
    <div class="question-content">{{ question.content }}</div>
    <div class="question-options">
      <div
        v-for="(option, oIdx) in question.options"
        :key="oIdx"
        class="option-item"
        :class="{ active: isSelected(option) }"
        @click="onSelect(option)"
      >
        <div class="option-marker" :class="{ active: isSelected(option) }">
          <span v-if="isSelected(option)" class="option-checked">
            <van-icon name="success" />
          </span>
          <span v-else class="option-label">{{ option.label }}</span>
        </div>
        <span class="option-content">{{ option.content }}</span>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.question-card {
  background: $card;
  border-radius: $radius;
  padding: 18px 16px;
  margin: 0 16px 12px;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.question-number {
  font-size: 16px;
  font-weight: 700;
  color: var(--primary);
}

.question-type {
  font-size: 11px;
  color: var(--primary);
  background: rgba(14, 116, 144, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
}

.question-score {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: auto;
}

.question-content {
  font-size: 15px;
  line-height: 1.6;
  color: var(--text);
  margin-bottom: 16px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;

  &:active {
    transform: scale(0.99);
  }

  &.active {
    border-color: var(--primary);
    background: rgba(14, 116, 144, 0.05);
  }
}

.option-marker {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  transition: all 0.2s;

  &.active {
    border-color: var(--primary);
    background: var(--primary);
    color: #fff;
  }
}

.option-content {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text);
  flex: 1;
  padding-top: 2px;
}
</style>
