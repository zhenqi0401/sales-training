<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { examsApi } from '@/api/exams'
import { showToast } from 'vant'
import type { WrongAnswer } from '@/types'

const router = useRouter()
const loading = ref(true)
const wrongAnswers = ref<WrongAnswer[]>([])

onMounted(async () => {
  try {
    const res = await examsApi.getWrongAnswers()
    wrongAnswers.value = res.data?.items || []
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const typeLabels: Record<string, string> = {
  single: '单选题',
  multi: '多选题',
  judge: '判断题'
}
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar
      title="错题本"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <EmptyState v-else-if="wrongAnswers.length === 0" description="暂无错题，继续保持！" />

    <div v-else class="wrong-list">
      <div
        v-for="item in wrongAnswers"
        :key="item.id"
        class="wrong-card"
      >
        <div class="wrong-header">
          <span class="wrong-type">{{ typeLabels[item.question?.type] || '' }}</span>
          <span class="wrong-count">错误 {{ item.wrongCount }} 次</span>
          <span class="wrong-date" v-if="item.lastWrongAt">{{ formatDate(item.lastWrongAt) }}</span>
        </div>

        <div class="wrong-question">{{ item.question?.content }}</div>

        <div class="wrong-answers">
          <div class="wrong-user-answer">
            <span class="answer-label">你的答案：</span>
            <span class="answer-value incorrect">{{ item.userAnswer }}</span>
          </div>
          <div class="wrong-correct-answer">
            <span class="answer-label">正确答案：</span>
            <span class="answer-value correct">{{ item.question?.answer }}</span>
          </div>
        </div>

        <div class="wrong-analysis" v-if="item.question?.analysis">
          <div class="analysis-title">
            <van-icon name="info-o" size="14" color="var(--primary)" />
            解析
          </div>
          <p class="analysis-text">{{ item.question.analysis }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-loading {
  padding: 60px 0;
}

.wrong-list {
  padding: 12px 16px;
}

.wrong-card {
  background: $card;
  border-radius: $radius;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  border-left: 3px solid var(--danger);
}

.wrong-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 12px;
}

.wrong-type {
  color: var(--primary);
  background: rgba(14, 116, 144, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
}

.wrong-count {
  color: var(--danger);
}

.wrong-date {
  color: var(--text-muted);
  margin-left: auto;
}

.wrong-question {
  font-size: 15px;
  line-height: 1.6;
  color: var(--text);
  margin-bottom: 12px;
}

.wrong-answers {
  margin-bottom: 12px;
}

.wrong-user-answer,
.wrong-correct-answer {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 4px;
  font-size: 14px;
}

.answer-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.answer-value {
  font-weight: 600;

  &.incorrect {
    color: var(--danger);
    text-decoration: line-through;
  }

  &.correct {
    color: var(--success);
  }
}

.wrong-analysis {
  background: linear-gradient(135deg, #ecfeff, #cffafe);
  border-radius: 8px;
  padding: 12px 14px;
}

.analysis-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--primary);
  margin-bottom: 6px;
}

.analysis-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
}
</style>
