<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ isEditing ? '编辑题目' : '新增题目' }}</h2>
      <p>{{ isEditing ? '修改题目信息' : '创建新的题目' }}</p>
    </div>

    <el-card shadow="hover">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="24">
          <el-col :span="8">
            <el-form-item label="题目类型" prop="type">
              <el-select v-model="form.type" placeholder="请选择" style="width: 100%">
                <el-option label="单选题" value="single" />
                <el-option label="多选题" value="multiple" />
                <el-option label="判断题" value="true_false" />
                <el-option label="填空题" value="fill_blank" />
                <el-option label="问答题" value="essay" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="所属分类" prop="categoryId">
              <el-tree-select
                v-model="form.categoryId"
                :data="categories"
                :props="treeProps"
                placeholder="请选择分类"
                check-strictly
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="难度" prop="difficulty">
              <el-select v-model="form.difficulty" placeholder="请选择" style="width: 100%">
                <el-option label="简单" value="easy" />
                <el-option label="中等" value="medium" />
                <el-option label="困难" value="hard" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="题目内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="3"
            placeholder="请输入题目内容"
          />
        </el-form-item>

        <!-- Options for single/multiple/true_false -->
        <el-form-item v-if="showOptions" label="选项">
          <div class="options-editor">
            <div
              v-for="(opt, index) in form.options"
              :key="index"
              class="option-row"
            >
              <span class="option-label">{{ opt.label }}.</span>
              <el-input
                v-model="opt.value"
                :placeholder="`选项 ${opt.label}`"
                class="option-input"
              />
              <el-button
                v-if="form.options.length > 2 && form.type !== 'true_false'"
                text
                type="danger"
                :icon="Close"
                @click="removeOption(index)"
              />
            </div>
            <el-button
              v-if="form.type !== 'true_false' && form.options.length < 6"
              type="primary"
              link
              @click="addOption"
            >
              <el-icon><Plus /></el-icon>添加选项
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="正确答案" prop="answer">
          <template v-if="form.type === 'single'">
            <el-select v-model="answerTextModel" placeholder="选择正确答案" style="width: 200px">
              <el-option v-for="opt in form.options" :key="opt.label" :label="opt.label" :value="opt.label" />
            </el-select>
          </template>
          <template v-else-if="form.type === 'multiple'">
            <el-checkbox-group v-model="answerArrayModel">
              <el-checkbox v-for="opt in form.options" :key="opt.label" :label="opt.label" :value="opt.label">
                {{ opt.label }}
              </el-checkbox>
            </el-checkbox-group>
          </template>
          <template v-else-if="form.type === 'true_false'">
            <el-radio-group v-model="answerTextModel">
              <el-radio value="正确">正确</el-radio>
              <el-radio value="错误">错误</el-radio>
            </el-radio-group>
          </template>
          <template v-else>
            <el-input v-model="answerTextModel" type="textarea" :rows="2" placeholder="请输入参考答案" style="width: 400px" />
          </template>
        </el-form-item>

        <el-form-item label="解析">
          <el-input
            v-model="form.explanation"
            type="textarea"
            :rows="2"
            placeholder="题目解析（选填）"
          />
        </el-form-item>

        <el-form-item label="标签">
          <el-select
            v-model="form.tags"
            multiple
            allow-create
            filterable
            placeholder="输入标签后按回车"
            style="width: 400px"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <div class="form-actions">
      <el-button type="primary" size="large" :loading="submitting" @click="handleSave">
        {{ submitting ? '保存中...' : '保存' }}
      </el-button>
      <el-button size="large" @click="() => $router.push('/questions')">取消</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Close } from '@element-plus/icons-vue'
import { getQuestionDetail, createQuestion, updateQuestion } from '@/api/questions'
import { getCategoryTree } from '@/api/categories'
import type { Category, Difficulty, QuestionOption, QuestionType } from '@/types'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const categories = ref<Category[]>([])
const treeProps = { label: 'name', value: 'id', children: 'children' } as any

const isEditing = computed(() => !!route.params.id)

const form = reactive({
  type: 'single' as QuestionType,
  categoryId: null as number | null,
  difficulty: 'medium' as Difficulty,
  content: '',
  options: [
    { label: 'A', value: '' },
    { label: 'B', value: '' },
    { label: 'C', value: '' },
    { label: 'D', value: '' },
  ] as QuestionOption[],
  answer: '' as string | string[],
  explanation: '',
  tags: [] as string[],
  status: 'active',
})

const showOptions = computed(() => ['single', 'multiple', 'true_false'].includes(form.type))
const answerTextModel = computed({
  get: () => Array.isArray(form.answer) ? form.answer.join(',') : form.answer,
  set: (value: string) => { form.answer = value },
})
const answerArrayModel = computed({
  get: () => Array.isArray(form.answer) ? form.answer : toAnswerArray(form.answer),
  set: (value: string[]) => { form.answer = value },
})

const rules: FormRules = {
  type: [{ required: true, message: '请选择题型', trigger: 'change' }],
  categoryId: [{ required: true, message: '请选择分类', trigger: 'change' }],
  difficulty: [{ required: true, message: '请选择难度', trigger: 'change' }],
  content: [{ required: true, message: '请输入题目内容', trigger: 'blur' }],
  answer: [{ required: true, message: '请设置正确答案', trigger: 'change' }],
}

// Reset options when type changes
watch(() => form.type, (newType) => {
  if (newType === 'true_false') {
    form.options = [
      { label: 'A', value: '正确' },
      { label: 'B', value: '错误' },
    ]
    form.answer = ''
  } else if (newType === 'single' || newType === 'multiple') {
    form.options = [
      { label: 'A', value: '' },
      { label: 'B', value: '' },
      { label: 'C', value: '' },
      { label: 'D', value: '' },
    ]
    form.answer = newType === 'multiple' ? [] : ''
  } else {
    form.options = []
    form.answer = ''
  }
})

const labelPool = 'ABCDEFGHIJ'

function addOption() {
  if (form.options.length >= 6) return
  const label = labelPool[form.options.length]
  form.options.push({ label, value: '' })
}

function removeOption(index: number) {
  form.options.splice(index, 1)
  // Relabel remaining options
  form.options.forEach((opt, i) => {
    opt.label = labelPool[i]
  })
}

onMounted(async () => {
  try {
    categories.value = await getCategoryTree()
  } catch { categories.value = [] }
  if (isEditing.value) {
    await loadQuestion()
  }
})

async function loadQuestion() {
  try {
    const q = await getQuestionDetail(Number(route.params.id))
    form.type = q.type
    form.categoryId = q.categoryId
    form.difficulty = q.difficulty
    form.content = q.content
    form.options = q.options || form.options
    form.answer = q.type === 'multiple' ? toAnswerArray(q.answer) : q.answer
    form.explanation = q.explanation || ''
    form.tags = q.tags
  } catch {
    ElMessage.error('加载题目信息失败')
  }
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const params = {
      type: form.type,
      categoryId: form.categoryId!,
      difficulty: form.difficulty,
      content: form.content,
      options: form.options,
      answer: form.answer,
      explanation: form.explanation,
      tags: form.tags,
    }

    if (isEditing.value) {
      await updateQuestion(Number(route.params.id), params)
      ElMessage.success('更新成功')
    } else {
      await createQuestion(params)
      ElMessage.success('创建成功')
    }
    router.push('/questions')
  } catch { /* handled by interceptor */ } finally {
    submitting.value = false
  }
}

function toAnswerArray(answer: string | string[]): string[] {
  if (Array.isArray(answer)) return answer
  return answer.split(',').map((item) => item.trim()).filter(Boolean)
}
</script>

<style scoped lang="scss">
.options-editor {
  .option-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;

    .option-label {
      width: 24px;
      font-weight: 700;
      color: #606266;
    }

    .option-input {
      flex: 1;
      max-width: 400px;
    }
  }
}

.form-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
