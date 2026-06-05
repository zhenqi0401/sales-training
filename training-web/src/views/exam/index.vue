<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'

const router = useRouter()

const exams = [
  {
    level: 'L1',
    title: '初级考核',
    description: '基础产品知识 + 接待流程',
    questionCount: 20,
    duration: 30,
    passScore: 60,
    totalScore: 100,
    icon: 'smile-o',
    color: 'var(--success)',
    bg: 'linear-gradient(135deg, #a7f3d0, #6ee7b7)'
  },
  {
    level: 'L2',
    title: '中级考核',
    description: '专业知识 + 销售技巧',
    questionCount: 30,
    duration: 45,
    passScore: 70,
    totalScore: 100,
    icon: 'star-o',
    color: 'var(--primary)',
    bg: 'linear-gradient(135deg, #a5f3fc, #67e8f9)'
  },
  {
    level: 'L3',
    title: '高级考核',
    description: '综合能力 + 实战场景',
    questionCount: 40,
    duration: 60,
    passScore: 80,
    totalScore: 100,
    icon: 'award-o',
    color: 'var(--warning)',
    bg: 'linear-gradient(135deg, #fde68a, #fcd34d)'
  }
]

// Sprint mode
const sprintMode = {
  level: 'sprint',
  title: '冲刺模式',
  description: '随机抽题，限时挑战',
  questionCount: 10,
  duration: 10,
  passScore: 60,
  totalScore: 100,
  icon: 'flash-o',
  color: 'var(--danger)',
  bg: 'linear-gradient(135deg, #fca5a5, #f87171)'
}

function startExam(level: string) {
  showToast('开始考试')
  router.push(`/exam/taking/${level.toLowerCase()}`)
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">在线考试</h2>
      <p class="page-subtitle">检验学习成果，查漏补缺</p>
    </div>

    <!-- Standard Exams -->
    <div class="exam-section">
      <h3 class="section-title">等级考核</h3>

      <div
        v-for="exam in exams"
        :key="exam.level"
        class="exam-card"
        @click="startExam(exam.level)"
      >
        <div class="exam-card-bg" :style="{ background: exam.bg }">
          <van-icon :name="exam.icon" size="36" :color="exam.color" />
        </div>
        <div class="exam-card-info">
          <div class="exam-title">{{ exam.title }}</div>
          <div class="exam-desc">{{ exam.description }}</div>
          <div class="exam-meta">
            <span>{{ exam.questionCount }}题</span>
            <span class="meta-dot">|</span>
            <span>{{ exam.duration }}分钟</span>
            <span class="meta-dot">|</span>
            <span>及格{{ exam.passScore }}分</span>
          </div>
        </div>
        <van-icon name="arrow" size="18" color="var(--text-muted)" />
      </div>
    </div>

    <!-- Sprint Mode -->
    <div class="exam-section">
      <h3 class="section-title">快速挑战</h3>

      <div class="sprint-card" @click="startExam(sprintMode.level)">
        <div class="sprint-icon">
          <van-icon :name="sprintMode.icon" size="48" :color="sprintMode.color" />
        </div>
        <div class="sprint-info">
          <div class="sprint-title">{{ sprintMode.title }}</div>
          <div class="sprint-desc">{{ sprintMode.description }}</div>
          <div class="sprint-meta">
            <span>{{ sprintMode.questionCount }}题</span>
            <span class="meta-dot">|</span>
            <span>{{ sprintMode.duration }}分钟快答</span>
          </div>
        </div>
        <div class="sprint-btn">
          <van-button round size="small" color="var(--danger)">开始</van-button>
        </div>
      </div>
    </div>

    <!-- Wrong Book Entry -->
    <div class="section-card" style="text-align: center;" @click="router.push('/exam/wrong-book')">
      <div class="wrong-book-entry">
        <van-icon name="notes-o" size="32" color="var(--primary)" />
        <div class="wrong-book-info">
          <div class="wrong-book-title">错题本</div>
          <div class="wrong-book-desc">查看历史错题，针对性复习</div>
        </div>
        <van-icon name="arrow" size="16" color="var(--text-muted)" />
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

.exam-section {
  padding: 12px 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}

.exam-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: $card;
  border-radius: $radius;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.2s;

  &:active {
    transform: translateX(4px);
  }
}

.exam-card-bg {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.exam-card-info {
  flex: 1;
  min-width: 0;
}

.exam-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.exam-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.exam-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
}

.meta-dot {
  color: var(--border);
}

// Sprint card
.sprint-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: $card;
  border-radius: $radius;
  padding: 16px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.2s;

  &:active {
    transform: translateX(4px);
  }
}

.sprint-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sprint-info {
  flex: 1;
  min-width: 0;
}

.sprint-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.sprint-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.sprint-meta {
  font-size: 11px;
  color: var(--text-muted);
}

.sprint-btn {
  flex-shrink: 0;
}

// Wrong book entry
.wrong-book-entry {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
}

.wrong-book-info {
  flex: 1;
  text-align: left;
}

.wrong-book-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 2px;
}

.wrong-book-desc {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
