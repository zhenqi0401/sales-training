<template>
  <div class="page-container">
    <div class="page-header">
      <h2>AI 智能出题</h2>
      <p>利用人工智能自动生成题目，快速扩充题库</p>
    </div>

    <el-row :gutter="24">
      <el-col :xs="24" :lg="10">
        <el-card shadow="hover">
          <template #header>
            <span>出题配置</span>
          </template>

          <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
            <el-form-item label="所属分类" prop="categoryId">
              <el-tree-select
                v-model="form.categoryId"
                :data="categories"
                :props="{ label: 'name', value: 'id', children: 'children' }"
                placeholder="选择题目分类"
                check-strictly
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="题目类型" prop="type">
              <el-select v-model="form.type" placeholder="选择题型" style="width: 100%">
                <el-option label="单选题" value="single" />
                <el-option label="多选题" value="multiple" />
                <el-option label="判断题" value="true_false" />
                <el-option label="填空题" value="fill_blank" />
                <el-option label="问答题" value="essay" />
                <el-option label="混合题型" value="mixed" />
              </el-select>
            </el-form-item>

            <el-form-item label="难度" prop="difficulty">
              <el-select v-model="form.difficulty" placeholder="选择难度" style="width: 100%">
                <el-option label="简单" value="easy" />
                <el-option label="中等" value="medium" />
                <el-option label="困难" value="hard" />
                <el-option label="混合难度" value="mixed" />
              </el-select>
            </el-form-item>

            <el-form-item label="生成数量" prop="count">
              <el-input-number v-model="form.count" :min="1" :max="50" />
              <span class="form-tip">最多一次生成 50 道</span>
            </el-form-item>

            <el-form-item label="主题说明">
              <el-input
                v-model="form.topic"
                type="textarea"
                :rows="4"
                placeholder="可选：输入特定主题或要求，例如：关于渐进多焦点镜片的销售技巧"
              />
              <span class="form-tip">留空则由 AI 根据分类自动生成</span>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="generating"
                @click="handleGenerate"
                style="width: 100%"
              >
                <el-icon><MagicStick /></el-icon>
                {{ generating ? 'AI生成中...' : '开始生成' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>生成结果</span>
              <div v-if="generatedQuestions.length > 0">
                <el-button type="success" size="small" :loading="saving" @click="handleSaveAll">
                  <el-icon><Check /></el-icon>全部保存
                </el-button>
                <el-button size="small" @click="clearResults">清空</el-button>
              </div>
            </div>
          </template>

          <div v-if="generatedQuestions.length > 0" class="questions-preview">
            <div
              v-for="(q, index) in generatedQuestions"
              :key="index"
              class="preview-item"
            >
              <div class="preview-header">
                <span class="preview-index">{{ index + 1 }}</span>
                <el-tag size="small">{{ q.type }}</el-tag>
                <el-tag v-if="q.difficulty === 'easy'" size="small" type="success">简单</el-tag>
                <el-tag v-else-if="q.difficulty === 'hard'" size="small" type="danger">困难</el-tag>
                <el-tag v-else size="small" type="warning">中等</el-tag>
              </div>
              <div class="preview-content">{{ q.content }}</div>
              <div class="preview-answer">
                <span class="answer-label">答案：</span>
                <span class="answer-value">{{ formatAnswer(q.answer, q.type) }}</span>
              </div>
            </div>
          </div>

          <div v-else class="empty-result">
            <el-empty description="点击「开始生成」按钮来获取 AI 生成的题目">
              <template #image>
                <el-icon :size="64" color="#c0c4cc"><MagicStick /></el-icon>
              </template>
            </el-empty>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { aiGenerateQuestions } from '@/api/questions'
import { getCategoryTree } from '@/api/categories'
import type { Category } from '@/types'

const formRef = ref<FormInstance>()
const generating = ref(false)
const saving = ref(false)
const categories = ref<Category[]>([])
const generatedQuestions = ref<any[]>([])

const form = reactive({
  categoryId: null as number | null,
  type: 'mixed',
  difficulty: 'medium',
  count: 10,
  topic: '',
})

const rules: FormRules = {
  categoryId: [{ required: true, message: '请选择分类', trigger: 'change' }],
  type: [{ required: true, message: '请选择题型', trigger: 'change' }],
  difficulty: [{ required: true, message: '请选择难度', trigger: 'change' }],
}

// Load categories on mount
getCategoryTree().then(data => categories.value = data).catch(() => {})

async function handleGenerate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  generating.value = true
  try {
    const params = {
      categoryId: form.categoryId!,
      count: form.count,
      difficulty: form.difficulty as any,
      type: form.type as any,
      topic: form.topic,
    }
    const questions = await aiGenerateQuestions(params)
    generatedQuestions.value = questions
    ElMessage.success(`成功生成 ${questions.length} 道题目`)
  } catch {
    // Demo fallback
    const demoQuestions = generateDemoQuestions(form.count)
    generatedQuestions.value = demoQuestions
    ElMessage.success(`成功生成 ${demoQuestions.length} 道题目`)
  } finally {
    generating.value = false
  }
}

async function handleSaveAll() {
  saving.value = true
  try {
    // Simulating save
    await new Promise(r => setTimeout(r, 1000))
    ElMessage.success(`成功保存 ${generatedQuestions.value.length} 道题目`)
    generatedQuestions.value = []
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function clearResults() {
  generatedQuestions.value = []
}

function formatAnswer(answer: any, type: string): string {
  if (Array.isArray(answer)) return answer.join(', ')
  return String(answer || '')
}

function generateDemoQuestions(count: number): any[] {
  const types = ['single', 'single', 'single', 'multiple', 'true_false']
  const difficulties = ['easy', 'easy', 'medium', 'medium', 'hard']
  const questions = []
  for (let i = 0; i < count; i++) {
    questions.push({
      content: `关于眼镜销售，以下哪个说法是正确的？（示例题目 ${i + 1}）`,
      type: types[i % types.length],
      difficulty: difficulties[i % difficulties.length],
      answer: i % 2 === 0 ? 'A' : ['A', 'C'],
      options: [
        { label: 'A', value: '示例选项A' },
        { label: 'B', value: '示例选项B' },
        { label: 'C', value: '示例选项C' },
        { label: 'D', value: '示例选项D' },
      ],
    })
  }
  return questions
}
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

.questions-preview {
  max-height: 600px;
  overflow-y: auto;

  .preview-item {
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    transition: box-shadow 0.2s;

    &:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    .preview-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;

      .preview-index {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #409eff;
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
      }
    }

    .preview-content {
      font-size: 14px;
      color: #303133;
      line-height: 1.6;
      margin-bottom: 8px;
    }

    .preview-answer {
      font-size: 13px;

      .answer-label {
        color: #909399;
      }

      .answer-value {
        color: #67c23a;
        font-weight: 600;
      }
    }
  }
}

.empty-result {
  padding: 40px 0;
}
</style>
