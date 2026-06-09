<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { examsApi } from '@/api/exams'
import type { QuestionOption, WrongAnswer } from '@/types'

const router = useRouter()
const loading = ref(true)
const wrongAnswers = ref<WrongAnswer[]>([])
const keyword = ref('')
const activeCategory = ref('全部')
const stats = ref({
  totalWrong: 0,
  weakCategories: [] as { name: string; count: number }[],
  weakKnowledgePoints: [] as { name: string; count: number }[]
})

const categories = computed(() => {
  const names = new Set<string>()
  wrongAnswers.value.forEach((item) => {
    const name = item.question?.categoryName || item.question?.knowledgePoint
    if (name) names.add(name)
  })
  return ['全部', ...Array.from(names)]
})

const filteredWrongAnswers = computed(() => {
  return wrongAnswers.value.filter((item) => {
    const question = item.question
    const category = question?.categoryName || question?.knowledgePoint || ''
    const optionText = question?.options?.map((option) => option.content).join(' ') || ''
    const matchesCategory = activeCategory.value === '全部' || category === activeCategory.value
    const text = `${question?.content || ''} ${optionText} ${question?.analysis || ''} ${category}`
    const matchesKeyword = !keyword.value || text.includes(keyword.value.trim())
    return matchesCategory && matchesKeyword
  })
})

const typeLabels: Record<string, string> = {
  single: '单选题',
  multi: '多选题',
  judge: '判断题'
}

onMounted(loadWrongBook)

async function loadWrongBook() {
  loading.value = true
  try {
    const [listRes, statsRes] = await Promise.all([
      examsApi.getWrongAnswers(1, 100),
      examsApi.getWrongAnswerStats()
    ])
    wrongAnswers.value = listRes.data?.items || []
    stats.value = statsRes.data || stats.value
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function normalizeAnswer(answer: string | string[] | undefined): string[] {
  if (!answer) return []
  if (Array.isArray(answer)) return answer.map((item) => String(item).trim()).filter(Boolean)
  return String(answer)
    .split(/[,，|、]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function answerText(answer: string | string[] | undefined) {
  const values = normalizeAnswer(answer)
  return values.length ? values.join('、') : '未作答'
}

function optionStatus(option: QuestionOption, item: WrongAnswer) {
  const userAnswers = normalizeAnswer(item.userAnswer)
  const correctAnswers = normalizeAnswer(item.question?.answer)
  const selected = userAnswers.includes(option.value)
  const correct = correctAnswers.includes(option.value)
  return {
    selected,
    correct,
    wrongSelected: selected && !correct
  }
}

function startWrongPractice() {
  if (wrongAnswers.value.length === 0) {
    showToast('暂无错题可练习')
    return
  }
  router.push('/exam/taking/wrong')
}
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar title="错题本" left-arrow fixed placeholder @click-left="router.back()" />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else>
      <div class="wrong-summary">
        <div class="summary-item">
          <span class="summary-value">{{ wrongAnswers.length }}</span>
          <span class="summary-label">错题数</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ stats.totalWrong }}</span>
          <span class="summary-label">累计错误</span>
        </div>
        <div class="summary-item">
          <span class="summary-value">{{ stats.weakCategories.length }}</span>
          <span class="summary-label">薄弱分类</span>
        </div>
      </div>

      <div class="wrong-tools">
        <van-search v-model="keyword" placeholder="搜索题目、选项、解析或知识点" shape="round" />
        <div class="category-scroll">
          <van-button
            v-for="category in categories"
            :key="category"
            round
            size="small"
            :type="activeCategory === category ? 'primary' : 'default'"
            @click="activeCategory = category"
          >
            {{ category }}
          </van-button>
        </div>
        <van-button round block type="primary" icon="replay" @click="startWrongPractice">
          错题重练
        </van-button>
      </div>

      <div v-if="stats.weakCategories.length || stats.weakKnowledgePoints.length" class="section-card">
        <h3 class="section-title">薄弱知识点分析</h3>
        <div class="weak-list" v-if="stats.weakCategories.length">
          <van-tag v-for="item in stats.weakCategories" :key="item.name" plain type="danger" size="medium">
            {{ item.name }} {{ item.count }}
          </van-tag>
        </div>
        <div class="weak-list" v-if="stats.weakKnowledgePoints.length">
          <van-tag v-for="item in stats.weakKnowledgePoints" :key="item.name" plain type="primary" size="medium">
            {{ item.name }} {{ item.count }}
          </van-tag>
        </div>
      </div>

      <EmptyState v-if="wrongAnswers.length === 0" description="暂无错题，继续保持！" />
      <EmptyState v-else-if="filteredWrongAnswers.length === 0" description="没有匹配的错题" />

      <div v-else class="wrong-list">
        <div v-for="item in filteredWrongAnswers" :key="item.id" class="wrong-card">
          <div class="wrong-header">
            <span class="wrong-type">{{ typeLabels[item.question?.type] || '' }}</span>
            <span class="wrong-category">{{ item.question?.categoryName || item.question?.knowledgePoint }}</span>
            <span class="wrong-count">错误 {{ item.wrongCount }} 次</span>
            <span class="wrong-date" v-if="item.lastWrongAt">{{ formatDate(item.lastWrongAt) }}</span>
          </div>

          <div class="wrong-question">{{ item.question?.content }}</div>

          <div class="wrong-options" v-if="item.question?.options?.length">
            <div
              v-for="option in item.question.options"
              :key="option.value"
              class="option-row"
              :class="{
                correct: optionStatus(option, item).correct,
                wrong: optionStatus(option, item).wrongSelected
              }"
              >
                <span class="option-label">{{ option.label || option.value }}</span>
                <span class="option-content">{{ option.content }}</span>
              </div>
            </div>

          <div class="wrong-answers">
            <div class="answer-row">
              <span class="answer-label">你的答案</span>
              <span class="answer-value incorrect">{{ answerText(item.userAnswer) }}</span>
            </div>
            <div class="answer-row">
              <span class="answer-label">正确答案</span>
              <span class="answer-value correct">{{ answerText(item.question?.answer) }}</span>
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
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page-loading {
  padding: 60px 0;
}

.wrong-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 14px 16px;
  background: $card;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.summary-value {
  color: var(--danger);
  font-size: 22px;
  font-weight: 700;
}

.summary-label {
  color: var(--text-muted);
  font-size: 12px;
}

.wrong-tools {
  padding: 10px 16px 14px;
  background: $card;
  margin-bottom: 8px;
}

.category-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 8px 0 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}

.weak-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
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
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 12px;
}

.wrong-type,
.wrong-category {
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

.wrong-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.option-row {
  display: grid;
  grid-template-columns: 26px 1fr;
  gap: 8px;
  align-items: flex-start;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f8fafc;
  font-size: 13px;

  &.correct {
    border-color: rgba(5, 150, 105, 0.35);
    background: #ecfdf5;
  }

  &.wrong {
    border-color: rgba(220, 38, 38, 0.35);
    background: #fef2f2;
  }
}

.option-label {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e2e8f0;
  color: var(--text-secondary);
  font-weight: 700;
  flex-shrink: 0;
}

.option-content {
  line-height: 1.5;
  color: var(--text);
  min-width: 0;
}

.wrong-answers {
  margin-bottom: 12px;
}

.answer-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
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
  background: #f0fdfa;
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
