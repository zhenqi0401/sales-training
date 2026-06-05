<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import DialogueBox from '@/components/script/DialogueBox.vue'

const route = useRoute()
const router = useRouter()

const moduleId = computed(() => Number(route.params.moduleId))
const loading = ref(false)
const content = ref<any>(null)

// Mock content based on module
const moduleContents: Record<number, any> = {
  1: {
    title: '接待流程演练',
    steps: [
      { type: 'knowledge', content: '标准接待流程：迎宾 → 问好 → 引导入座 → 了解需求 → 产品介绍 → 试戴体验 → 送客' },
      { type: 'dialogue', role: 'teacher', name: '导师', content: '顾客进店时，你应该怎么做？先主动迎宾问好，然后用标准手势引导顾客入座。' },
      { type: 'dialogue', role: 'student', name: '学员', content: '欢迎光临XX眼镜！请这边坐，我来为您服务。请问您是想配眼镜还是看看其他产品？' },
      { type: 'dialogue', role: 'teacher', name: '导师', content: '很好！记住要微笑服务，保持眼神交流。现在让我们继续了解顾客需求...' }
    ]
  },
  2: {
    title: '问诊话术演练',
    steps: [
      { type: 'knowledge', content: '专业问诊要点：用眼习惯、佩戴史、需求场景、预算范围' },
      { type: 'dialogue', role: 'teacher', name: '导师', content: '问诊是了解顾客需求的关键环节，要从多个维度进行询问。' },
      { type: 'dialogue', role: 'student', name: '学员', content: '请问您平时主要是在什么场景下戴眼镜？看远比较多还是看近比较多？' },
      { type: 'dialogue', role: 'teacher', name: '导师', content: '问得很好！接下来要了解顾客之前的佩戴情况和预算...' }
    ]
  },
  7: {
    title: '售后服务演练',
    steps: [
      { type: 'knowledge', content: '售后回访流程：确认满意度 → 解答疑问 → 提醒保养 → 邀请复购' },
      { type: 'dialogue', role: 'teacher', name: '导师', content: '售后回访是维护老客户的重要手段，记得在配镜后3-7天进行回访。' },
      { type: 'dialogue', role: 'student', name: '学员', content: '您好，我是XX眼镜的小王，您上周配的眼镜戴着还舒服吗？有没有什么不适或者疑问？' }
    ]
  }
}

const moduleNames: Record<number, string> = {
  1: '接待流程演练', 2: '问诊话术演练', 3: '产品介绍演练',
  4: '异议处理演练', 5: '成交技巧演练', 6: '验光配镜演练', 7: '售后服务演练'
}

const moduleTitle = computed(() => moduleNames[moduleId.value] || '演练模块')

onMounted(() => {
  content.value = moduleContents[moduleId.value] || moduleContents[1]
})
</script>

<template>
  <div class="page-no-tabbar">
    <van-nav-bar
      :title="moduleTitle"
      left-arrow
      fixed
      placeholder
      @click-left="router.back()"
    />

    <van-loading v-if="loading" size="24" class="page-loading" />

    <template v-else-if="content">
      <!-- Module Header -->
      <div class="module-header">
        <div class="header-icon">
          <van-icon name="fire-o" size="32" color="var(--primary)" />
        </div>
        <h2 class="header-title">{{ content.title }}</h2>
        <p class="header-desc">通过情景对话学习，提升实战能力</p>
      </div>

      <!-- Content Steps -->
      <div class="content-steps">
        <div
          v-for="(step, idx) in content.steps"
          :key="idx"
          class="step-item"
        >
          <!-- Knowledge Point -->
          <div v-if="step.type === 'knowledge'" class="knowledge-point">
            <div class="kp-title">
              <van-icon name="info-o" size="14" color="var(--primary)" />
              知识点
            </div>
            <p class="kp-content">{{ step.content }}</p>
          </div>

          <!-- Dialogue -->
          <DialogueBox
            v-else-if="step.type === 'dialogue'"
            :role="step.role"
            :name="step.name"
            :content="step.content"
          />

          <!-- Quiz / Simulation -->
          <div v-else-if="step.type === 'quiz'" class="quiz-box">
            <div class="quiz-question">{{ step.content }}</div>
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

.module-header {
  text-align: center;
  padding: 24px 16px;
  background: $card;
}

.header-icon {
  margin-bottom: 12px;
}

.header-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 6px;
}

.header-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.content-steps {
  padding: 16px 0;
}

.step-item {
  margin-bottom: 8px;
}

.knowledge-point {
  background: linear-gradient(135deg, #ecfeff, #cffafe);
  border-radius: 8px;
  padding: 14px 18px;
  margin: 0 16px 16px;
  border-left: 3px solid var(--primary);
}

.kp-title {
  font-weight: 700;
  color: var(--primary);
  font-size: 14px;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.kp-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
}
</style>
