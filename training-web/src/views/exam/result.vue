<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { examsApi } from '@/api/exams'
import ResultBox from '@/components/exam/ResultBox.vue'
import type { ExamRecord, Question, UserAnswer } from '@/types'

const route = useRoute()
const router = useRouter()

const recordId = computed(() => Number(route.params.recordId))
const record = ref<ExamRecord | null>(null)
const loading = ref(true)

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
  if (record.value) {
    router.push(`/exam/taking/${record.value.examLevel.toLowerCase()}`)
  }
}

function goHome() {
  router.push('/home')
}
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar
      title="考试结果"
      left-text="返回"
      @click-left="router.push('/exam')"
    />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else-if="record">
      <div class="result-page">
        <div class="result-section">
          <div class="result-title">
            {{ record.passed ? '恭喜通过！' : '未通过' }}
          </div>

          <ResultBox :record="record" />
        </div>

        <!-- Answer Breakdown -->
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
              <span class="b-value rate">{{ record.totalCount > 0 ? Math.round((record.correctCount / record.totalCount) * 100) : 0 }}%</span>
            </div>
          </div>
        </div>

        <!-- Knowledge Points to Review -->
        <div class="section-card" v-if="!record.passed">
          <h3 class="breakdown-title">复习建议</h3>
          <div class="review-tips">
            <div class="tip-item">
              <van-icon name="info-o" size="16" color="var(--primary)" />
              <span>建议重新学习相关课程内容</span>
            </div>
            <div class="tip-item">
              <van-icon name="notes-o" size="16" color="var(--primary)" />
              <span>查看错题本中的详细解析</span>
            </div>
            <div class="tip-item">
              <van-icon name="replay" size="16" color="var(--primary)" />
              <span>3天后可再次参加考试</span>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="result-actions">
          <van-button
            round
            block
            color="linear-gradient(135deg, var(--primary), var(--primary-dark))"
            @click="retryExam"
          >
            {{ record.passed ? '再次挑战' : '重新考试' }}
          </van-button>
          <van-button
            round
            plain
            type="primary"
            @click="goWrongBook"
            style="margin-left: 12px;"
          >
            查看错题
          </van-button>
          <van-button
            round
            plain
            type="default"
            @click="goHome"
            style="margin-left: 12px;"
          >
            返回首页
          </van-button>
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
  display: flex;
  justify-content: center;
  padding: 24px 16px;

  .van-button {
    flex: 1;
  }
}
</style>
