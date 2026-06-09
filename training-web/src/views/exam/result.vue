<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { examsApi } from '@/api/exams'
import ResultBox from '@/components/exam/ResultBox.vue'
import type { ExamRecord, UserAnswer } from '@/types'

const route = useRoute()
const router = useRouter()

const recordId = computed(() => Number(route.params.recordId))
const record = ref<ExamRecord | null>(null)
const loading = ref(true)

const wrongAnswers = computed(() => {
  return (record.value?.answers || []).filter((answer) => !(answer.isCorrect ?? answer.correct))
})

onMounted(async () => {
  try {
    const res = await examsApi.getExamRecord(recordId.value)
    record.value = res.data
  } catch {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

function goWrongBook() {
  router.push('/exam/wrong-book')
}

function retryExam() {
  if (!record.value) return
  router.push(`/exam/taking/${record.value.examLevel.toLowerCase()}`)
}

function goHome() {
  router.push('/home')
}

function answerText(answer: string | string[] | undefined) {
  if (!answer || (Array.isArray(answer) && answer.length === 0)) return '未作答'
  return Array.isArray(answer) ? answer.join('、') : answer
}

function selectedText(answer: UserAnswer) {
  return answerText(answer.userAnswer || answer.selected)
}
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar title="考试结果" left-text="返回" @click-left="router.push('/exam')" />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else-if="record">
      <div class="result-page">
        <div class="result-section">
          <div class="result-title">{{ record.passed ? '恭喜通过' : '未通过' }}</div>
          <ResultBox :record="record" />
        </div>

        <div class="section-card">
          <h3 class="breakdown-title">答题详情</h3>
          <div class="breakdown-stats">
            <div class="breakdown-item">
              <span class="b-label">正确</span>
              <span class="b-value correct">{{ record.correctCount }}</span>
            </div>
            <div class="breakdown-item">
              <span class="b-label">错误</span>
              <span class="b-value wrong">{{ record.totalCount - record.correctCount }}</span>
            </div>
            <div class="breakdown-item">
              <span class="b-label">正确率</span>
              <span class="b-value rate">
                {{ record.totalCount > 0 ? Math.round((record.correctCount / record.totalCount) * 100) : 0 }}%
              </span>
            </div>
          </div>
        </div>

        <div class="section-card" v-if="record.categoryScores?.length">
          <h3 class="breakdown-title">分类得分</h3>
          <div v-for="item in record.categoryScores" :key="item.category" class="category-row">
            <div class="category-head">
              <span>{{ item.category }}</span>
              <span>{{ item.score }}/{{ item.totalScore }}</span>
            </div>
            <van-progress
              :percentage="item.totalScore > 0 ? Math.round((item.score / item.totalScore) * 100) : 0"
              :stroke-width="6"
              color="var(--primary)"
              track-color="#e2e8f0"
              :show-pivot="false"
            />
            <div class="category-meta">答对 {{ item.correctCount }}/{{ item.totalCount }} 题</div>
          </div>
        </div>

        <div class="section-card" v-if="wrongAnswers.length">
          <h3 class="breakdown-title">错题解析</h3>
          <div v-for="answer in wrongAnswers" :key="answer.questionId" class="wrong-answer-card">
            <div class="wrong-question">{{ answer.question?.content }}</div>
            <div class="answer-line">
              <span>你的答案</span>
              <strong class="wrong">{{ selectedText(answer) }}</strong>
            </div>
            <div class="answer-line">
              <span>正确答案</span>
              <strong class="correct">{{ answer.correctAnswer || answer.question?.answer }}</strong>
            </div>
            <div class="analysis-box" v-if="answer.analysis || answer.question?.analysis">
              {{ answer.analysis || answer.question?.analysis }}
            </div>
            <van-tag v-if="answer.knowledgePoint" plain type="primary">{{ answer.knowledgePoint }}</van-tag>
          </div>
        </div>

        <div class="section-card" v-if="record.weakPoints?.length">
          <h3 class="breakdown-title">复习建议</h3>
          <div class="review-tips">
            <div v-for="point in record.weakPoints" :key="point" class="tip-item">
              <van-icon name="info-o" size="16" color="var(--primary)" />
              <span>建议重点复习：{{ point }}</span>
            </div>
          </div>
        </div>

        <div class="result-actions">
          <van-button round block color="linear-gradient(135deg, var(--primary), var(--primary-dark))" @click="retryExam">
            {{ record.passed ? '再次挑战' : '重新考试' }}
          </van-button>
          <van-button round plain type="primary" @click="goWrongBook">查看错题</van-button>
          <van-button round plain type="default" @click="goHome">返回首页</van-button>
        </div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page-loading {
  padding: 60px 0;
}

.result-page {
  padding: 16px 0;
}

.result-section {
  text-align: center;
  padding: 0 16px;
}

.result-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 16px;
}

.breakdown-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}

.breakdown-stats {
  display: flex;
  justify-content: space-around;
}

.breakdown-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.b-label {
  font-size: 12px;
  color: var(--text-muted);
}

.b-value {
  font-size: 24px;
  font-weight: 700;

  &.correct {
    color: var(--success);
  }

  &.wrong {
    color: var(--danger);
  }

  &.rate {
    color: var(--primary);
  }
}

.category-row {
  margin-bottom: 14px;

  &:last-child {
    margin-bottom: 0;
  }
}

.category-head,
.category-meta,
.answer-line {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}

.category-head {
  margin-bottom: 6px;
  font-weight: 600;
  color: var(--text);
}

.category-meta {
  margin-top: 4px;
  color: var(--text-muted);
}

.wrong-answer-card {
  padding: 12px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: none;
  }
}

.wrong-question {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
  margin-bottom: 10px;
}

.answer-line {
  margin-bottom: 6px;
  color: var(--text-muted);

  .wrong {
    color: var(--danger);
  }

  .correct {
    color: var(--success);
  }
}

.analysis-box {
  margin: 10px 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f0fdfa;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.review-tips {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

.result-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  padding: 24px 16px;
}
</style>
