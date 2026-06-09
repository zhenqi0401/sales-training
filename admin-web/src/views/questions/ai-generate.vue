<template>
  <div class="page-container">
    <div class="page-header">
      <h2>AI 生成题目</h2>
      <p>选择视频并配置生成规则，管理员审核通过后再写入题库</p>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="9">
        <el-card shadow="hover">
          <template #header>
            <span>生成配置</span>
          </template>

          <el-form ref="formRef" :model="form" :rules="rules" label-width="118px">
            <el-form-item label="关联视频" prop="videoId">
              <el-select
                v-model="form.videoId"
                filterable
                placeholder="选择要出题的视频"
                style="width: 100%"
                @change="handleVideoChange"
              >
                <el-option
                  v-for="video in videos"
                  :key="video.id"
                  :label="video.title"
                  :value="video.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="题目分类" prop="categoryId">
              <el-tree-select
                v-model="form.categoryId"
                :data="categories"
                :props="treeProps"
                placeholder="选择入库分类"
                check-strictly
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="产品分类">
              <el-tree-select
                v-model="form.productCategoryId"
                :data="categories"
                :props="treeProps"
                placeholder="默认使用视频分类"
                check-strictly
                clearable
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="题目数量" prop="count">
              <el-input-number v-model="form.count" :min="1" :max="50" />
            </el-form-item>

            <el-form-item label="难度级别" prop="difficultyLevel">
              <el-segmented
                v-model="form.difficultyLevel"
                :options="difficultyOptions"
              />
            </el-form-item>

            <el-form-item label="题型比例">
              <div class="ratio-list">
                <div class="ratio-row">
                  <span>单选</span>
                  <el-slider v-model="form.questionTypeRatios.single" :min="0" :max="100" />
                  <el-input-number v-model="form.questionTypeRatios.single" :min="0" :max="100" size="small" />
                </div>
                <div class="ratio-row">
                  <span>多选</span>
                  <el-slider v-model="form.questionTypeRatios.multiple" :min="0" :max="100" />
                  <el-input-number v-model="form.questionTypeRatios.multiple" :min="0" :max="100" size="small" />
                </div>
                <div class="ratio-row">
                  <span>判断</span>
                  <el-slider v-model="form.questionTypeRatios.true_false" :min="0" :max="100" />
                  <el-input-number v-model="form.questionTypeRatios.true_false" :min="0" :max="100" size="small" />
                </div>
                <span class="form-tip">比例按权重计算，不要求总和等于 100</span>
              </div>
            </el-form-item>

            <el-form-item label="知识点">
              <el-select
                v-model="form.knowledgePoints"
                multiple
                allow-create
                filterable
                default-first-option
                placeholder="输入后回车，如：产品知识、异议处理"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="补充要求">
              <el-input
                v-model="form.topic"
                type="textarea"
                :rows="3"
                placeholder="可填写重点场景、产品卖点或出题要求"
              />
            </el-form-item>

            <el-form-item label="字幕/转写">
              <el-input
                v-model="form.transcript"
                type="textarea"
                :rows="4"
                placeholder="可选。未填写时后端会调用 ASR 占位方法"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="generating"
                style="width: 100%"
                @click="handleGenerate"
              >
                <el-icon><MagicStick /></el-icon>
                {{ generating ? '生成中...' : 'AI 生成题目' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="15">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>管理员审核</span>
              <div v-if="generatedQuestions.length" class="header-actions">
                <el-button size="small" @click="addQuestion">
                  <el-icon><Plus /></el-icon>补充题目
                </el-button>
                <el-button type="success" size="small" :loading="saving" @click="handleSaveAll">
                  <el-icon><Check /></el-icon>审核通过并入库
                </el-button>
                <el-button size="small" @click="clearResults">清空</el-button>
              </div>
            </div>
          </template>

          <div v-if="generatedQuestions.length" class="review-list">
            <el-form label-width="86px">
              <div
                v-for="(question, index) in generatedQuestions"
                :key="question.localId"
                class="review-item"
              >
                <div class="review-title">
                  <div class="title-left">
                    <span class="preview-index">{{ index + 1 }}</span>
                    <el-select v-model="question.type" size="small" class="type-select" @change="resetQuestionOptions(question)">
                      <el-option label="单选题" value="single" />
                      <el-option label="多选题" value="multiple" />
                      <el-option label="判断题" value="true_false" />
                    </el-select>
                    <el-tag size="small">{{ difficultyText(question.difficulty) }}</el-tag>
                  </div>
                  <el-button text type="danger" :icon="Delete" @click="removeQuestion(index)">删除</el-button>
                </div>

                <el-form-item label="题干">
                  <el-input v-model="question.content" type="textarea" :rows="2" />
                </el-form-item>

                <el-form-item label="选项">
                  <div class="options-editor">
                    <div v-for="option in question.options" :key="option.label" class="option-row">
                      <span>{{ option.label }}.</span>
                      <el-input v-model="option.value" />
                    </div>
                  </div>
                </el-form-item>

                <el-form-item label="正确答案">
                  <el-select
                    v-if="question.type === 'single' || question.type === 'true_false'"
                    v-model="question.answer"
                    placeholder="选择答案"
                    style="width: 180px"
                  >
                    <el-option v-for="option in question.options" :key="option.label" :label="option.label" :value="option.label" />
                  </el-select>
                  <el-select
                    v-else
                    v-model="question.answer"
                    multiple
                    placeholder="选择答案"
                    style="width: 260px"
                  >
                    <el-option v-for="option in question.options" :key="option.label" :label="option.label" :value="option.label" />
                  </el-select>
                </el-form-item>

                <el-form-item label="解析">
                  <el-input v-model="question.explanation" type="textarea" :rows="2" />
                </el-form-item>

                <el-form-item label="标签">
                  <el-select
                    v-model="question.tags"
                    multiple
                    allow-create
                    filterable
                    default-first-option
                    placeholder="输入标签"
                    style="width: 100%"
                  />
                </el-form-item>
              </div>
            </el-form>
          </div>

          <div v-else class="empty-result">
            <el-empty description="选择视频并点击 AI 生成题目">
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
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Check, Delete, MagicStick, Plus } from '@element-plus/icons-vue'
import { aiGenerateQuestions, saveReviewedAiQuestions } from '@/api/questions'
import { getCategoryTree } from '@/api/categories'
import { getVideoList } from '@/api/videos'
import type { AiGenerateParams, Category, Question, QuestionOption, Video } from '@/types'

type ReviewQuestion = Omit<Partial<Question>, 'answer'> & {
  localId: string
  type: 'single' | 'multiple' | 'true_false'
  categoryId: number | null
  videoId: number | null
  content: string
  options: QuestionOption[]
  answer: string | string[]
  explanation: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
}

const router = useRouter()
const formRef = ref<FormInstance>()
const generating = ref(false)
const saving = ref(false)
const categories = ref<Category[]>([])
const videos = ref<Video[]>([])
const generatedQuestions = ref<ReviewQuestion[]>([])
const treeProps = { label: 'name', value: 'id', children: 'children' } as any
const difficultyOptions = [
  { label: 'L1', value: 'L1' },
  { label: 'L2', value: 'L2' },
  { label: 'L3', value: 'L3' },
]

const form = reactive<AiGenerateParams>({
  videoId: 0,
  categoryId: null,
  productCategoryId: null,
  count: 10,
  difficultyLevel: 'L2',
  questionTypeRatios: {
    single: 60,
    multiple: 30,
    true_false: 10,
  },
  knowledgePoints: ['产品知识'],
  topic: '',
  transcript: '',
})

const rules: FormRules = {
  videoId: [{ required: true, message: '请选择视频', trigger: 'change' }],
  categoryId: [{ required: true, message: '请选择题目分类', trigger: 'change' }],
  count: [{ required: true, message: '请输入题目数量', trigger: 'change' }],
  difficultyLevel: [{ required: true, message: '请选择难度', trigger: 'change' }],
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadVideos()])
})

async function loadCategories() {
  try {
    categories.value = await getCategoryTree()
  } catch {
    categories.value = []
  }
}

async function loadVideos() {
  try {
    const data = await getVideoList({ page: 1, pageSize: 100, status: 'published' })
    videos.value = data.list
  } catch {
    videos.value = []
  }
}

function handleVideoChange(videoId: number) {
  const video = videos.value.find((item) => item.id === videoId)
  if (!video) return
  if (!form.categoryId) form.categoryId = video.categoryId
  if (!form.productCategoryId) form.productCategoryId = video.categoryId
  const tags = new Set([...(form.knowledgePoints ?? []), ...(video.tags ?? [])])
  form.knowledgePoints = Array.from(tags).filter(Boolean)
}

async function handleGenerate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  generating.value = true
  try {
    const questions = await aiGenerateQuestions(form)
    generatedQuestions.value = questions.map(toReviewQuestion)
    ElMessage.success(`已生成 ${questions.length} 道待审核题目`)
  } catch {
    // handled by interceptor
  } finally {
    generating.value = false
  }
}

async function handleSaveAll() {
  if (!generatedQuestions.value.length) return
  const invalidIndex = generatedQuestions.value.findIndex((question) => !isQuestionValid(question))
  if (invalidIndex >= 0) {
    ElMessage.warning(`第 ${invalidIndex + 1} 题内容不完整`)
    return
  }

  saving.value = true
  try {
    await saveReviewedAiQuestions(generatedQuestions.value)
    ElMessage.success(`已入库 ${generatedQuestions.value.length} 道题目`)
    generatedQuestions.value = []
    router.push('/questions')
  } catch {
    // handled by interceptor
  } finally {
    saving.value = false
  }
}

function addQuestion() {
  generatedQuestions.value.push(toReviewQuestion({
    type: 'single',
    categoryId: form.categoryId,
    videoId: form.videoId,
    content: '',
    options: defaultOptions('single'),
    answer: '',
    explanation: '',
    difficulty: difficultyFromLevel(form.difficultyLevel),
    tags: ['产品知识'],
  } as any))
}

function removeQuestion(index: number) {
  generatedQuestions.value.splice(index, 1)
}

function clearResults() {
  generatedQuestions.value = []
}

function resetQuestionOptions(question: ReviewQuestion) {
  question.options = defaultOptions(question.type)
  question.answer = question.type === 'multiple' ? [] : ''
}

function toReviewQuestion(question: Partial<Question>): ReviewQuestion {
  const type = ['single', 'multiple', 'true_false'].includes(String(question.type)) ? question.type as ReviewQuestion['type'] : 'single'
  return {
    localId: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    type,
    categoryId: question.categoryId ?? form.categoryId ?? null,
    videoId: question.videoId ?? form.videoId ?? null,
    content: question.content ?? '',
    options: question.options?.length ? question.options : defaultOptions(type),
    answer: type === 'multiple' ? toAnswerArray(question.answer ?? []) : String(question.answer ?? ''),
    explanation: question.explanation ?? '',
    difficulty: question.difficulty ?? difficultyFromLevel(form.difficultyLevel),
    tags: question.tags?.length ? question.tags : ['产品知识'],
    status: 'active',
    source: 'ai',
  }
}

function defaultOptions(type: ReviewQuestion['type']): QuestionOption[] {
  if (type === 'true_false') {
    return [
      { label: 'A', value: '正确' },
      { label: 'B', value: '错误' },
    ]
  }
  return [
    { label: 'A', value: '' },
    { label: 'B', value: '' },
    { label: 'C', value: '' },
    { label: 'D', value: '' },
  ]
}

function isQuestionValid(question: ReviewQuestion): boolean {
  const hasContent = question.content.trim().length > 0
  const hasAnswer = Array.isArray(question.answer)
    ? question.answer.length > 0
    : String(question.answer || '').trim().length > 0
  const hasOptions = question.options.every((option) => option.value.trim().length > 0)
  return hasContent && hasAnswer && hasOptions && !!question.categoryId && !!question.videoId
}

function difficultyFromLevel(level: string): 'easy' | 'medium' | 'hard' {
  if (level === 'L1') return 'easy'
  if (level === 'L3') return 'hard'
  return 'medium'
}

function difficultyText(difficulty: string): string {
  if (difficulty === 'easy') return 'L1'
  if (difficulty === 'hard') return 'L3'
  return 'L2'
}

function toAnswerArray(answer: unknown): string[] {
  if (Array.isArray(answer)) return answer.map(String)
  return String(answer || '').split(',').map((item) => item.trim()).filter(Boolean)
}
</script>

<style scoped lang="scss">
.card-header,
.review-title,
.title-left,
.header-actions {
  display: flex;
  align-items: center;
}

.card-header,
.review-title {
  justify-content: space-between;
}

.title-left,
.header-actions {
  gap: 8px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
}

.ratio-list {
  width: 100%;
}

.ratio-row {
  display: grid;
  grid-template-columns: 42px minmax(120px, 1fr) 92px;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.review-list {
  max-height: 720px;
  overflow-y: auto;
  padding-right: 4px;
}

.review-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 14px;
  background: #fff;
}

.review-title {
  margin-bottom: 14px;
}

.preview-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.type-select {
  width: 108px;
}

.options-editor {
  width: 100%;
}

.option-row {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.empty-result {
  padding: 48px 0;
}
</style>
