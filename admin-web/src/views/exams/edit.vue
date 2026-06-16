<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ isEditing ? '编辑试卷' : '新增试卷' }}</h2>
      <p>{{ isEditing ? '修改试卷信息及题目' : '创建新的考试试卷' }}</p>
    </div>

    <el-row :gutter="24">
      <el-col :span="16">
        <!-- Basic Info -->
        <el-card shadow="hover" class="mb-4">
          <template #header><span>基本信息</span></template>
          <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
            <el-form-item label="试卷标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入试卷标题" maxlength="100" />
            </el-form-item>
            <el-form-item label="组卷方式" prop="type">
              <el-radio-group v-model="form.type">
                <el-radio value="manual">手动组卷</el-radio>
                <el-radio value="random">随机组卷</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="考试时长" prop="duration" label-width="100px">
                  <el-input-number v-model="form.duration" :min="1" :max="240" /> 分钟
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="总分" prop="totalScore" label-width="80px">
                  <el-input-number v-model="form.totalScore" :min="0" :max="500" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="及格分" prop="passScore" label-width="80px">
                  <el-input-number v-model="form.passScore" :min="0" :max="form.totalScore" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="考试时间">
              <el-date-picker
                v-model="dateRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="3" placeholder="试卷说明" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- Questions (Manual mode) -->
        <el-card v-if="form.type === 'manual'" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>题目列表（{{ questions.length }} 题）</span>
              <el-button type="primary" size="small" @click="openQuestionPicker">
                <el-icon><Plus /></el-icon>添加题目
              </el-button>
            </div>
          </template>

          <el-table :data="questions" stripe size="small">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="content" label="题目" min-width="300" show-overflow-tooltip />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">
                <el-tag size="small">{{ typeLabel(row.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="分数" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.score" :min="1" :max="100" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60">
              <template #default="{ row }">
                <el-button text type="danger" size="small" @click="removeQuestion(row)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="questions.length === 0" description="请点击「添加题目」按钮添加题目" />
        </el-card>

        <!-- Random mode settings -->
        <el-card v-else shadow="hover">
          <template #header><span>随机组卷设置</span></template>
          <el-form label-width="120px">
            <el-form-item label="题目数量">
              <el-input-number v-model="randomCount" :min="1" :max="200" />
            </el-form-item>
            <el-form-item label="选题分类">
              <el-tree-select
                v-model="randomCategories"
                :data="categoryTree"
                :props="treeProps"
                multiple
                check-strictly
                placeholder="选择题目分类（可多选）"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleRandomPreview">
                <el-icon><Refresh /></el-icon>预览题目
              </el-button>
            </el-form-item>
          </el-form>
          <div v-if="previewQuestions.length > 0">
            <el-divider>预览题目（{{ previewQuestions.length }} 题）</el-divider>
            <div v-for="(q, i) in previewQuestions" :key="i" class="preview-item">
              <span class="preview-num">{{ i + 1 }}.</span>
              {{ q.content }}
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>试卷概要</span></template>
          <div class="summary-item">
            <span class="label">试卷标题</span>
            <span class="value">{{ form.title || '未填写' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">组卷方式</span>
            <span class="value">{{ form.type === 'manual' ? '手动组卷' : '随机组卷' }}</span>
          </div>
          <div class="summary-item">
            <span class="label">题目数量</span>
            <span class="value">{{ form.type === 'manual' ? questions.length : randomCount }}</span>
          </div>
          <div class="summary-item">
            <span class="label">考试时长</span>
            <span class="value">{{ form.duration }} 分钟</span>
          </div>
          <div class="summary-item">
            <span class="label">总分</span>
            <span class="value">{{ form.totalScore }} 分</span>
          </div>
          <div class="summary-item">
            <span class="label">及格分数</span>
            <span class="value">{{ form.passScore }} 分 <template v-if="form.totalScore">({{ Math.round(form.passScore / form.totalScore * 100) }}%)</template></span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="form-actions">
      <el-button type="primary" size="large" :loading="submitting" @click="handleSave">保存</el-button>
      <el-button size="large" @click="$router.push('/exams')">取消</el-button>
    </div>

    <!-- Question Picker Dialog -->
    <el-dialog v-model="showQuestionPicker" title="选择题目" width="800px">
      <el-input v-model="pickerKeyword" placeholder="搜索题目" clearable style="margin-bottom: 16px" />
      <el-table :data="availableQuestions" stripe size="small" @selection-change="onPickerSelect">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="content" label="题目内容" min-width="250" show-overflow-tooltip />
        <el-table-column label="类型" width="80">
          <template #default="{ row }"> <el-tag size="small">{{ typeLabel(row.type) }}</el-tag> </template>
        </el-table-column>
        <el-table-column label="难度" width="70">
          <template #default="{ row }">
            <span :class="'diff-' + row.difficulty">{{ diffLabel(row.difficulty) }}</span>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="showQuestionPicker = false">取消</el-button>
        <el-button type="primary" @click="addSelectedQuestions">添加（{{ pickerSelected.length }} 题）</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getExamDetail, createExam, updateExam } from '@/api/exams'
import { getQuestionList } from '@/api/questions'
import { getCategoryTree } from '@/api/categories'
import type { Category } from '@/types'

const route = useRoute()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const isEditing = computed(() => !!route.params.id)
const categoryTree = ref<Category[]>([])
const treeProps = { label: 'name', value: 'id', children: 'children' } as any

// Form state
const form = reactive({
  title: '',
  type: 'manual',
  duration: 60,
  totalScore: 100,
  passScore: 60,
  description: '',
  startTime: undefined as string | undefined,
  endTime: undefined as string | undefined,
})
const dateRange = ref<[Date, Date] | null>(null)
const questions = ref<any[]>([])
const randomCount = ref(20)
const randomCategories = ref<number[]>([])
const previewQuestions = ref<any[]>([])

// Question picker
const showQuestionPicker = ref(false)
const pickerKeyword = ref('')
const availableQuestions = ref<any[]>([])
const pickerSelected = ref<any[]>([])

const rules: FormRules = {
  title: [{ required: true, message: '请输入试卷标题', trigger: 'blur' }],
  type: [{ required: true, message: '请选择组卷方式', trigger: 'change' }],
}

onMounted(async () => {
  try { categoryTree.value = await getCategoryTree() } catch { categoryTree.value = [] }
  if (isEditing.value) await loadExam()
})

async function loadExam() {
  try {
    const exam = await getExamDetail(Number(route.params.id))
    form.title = exam.title
    form.type = exam.type
    form.duration = exam.duration
    form.totalScore = exam.totalScore
    form.passScore = exam.passScore
    form.description = exam.description || ''
    questions.value = (exam.questions || []).map((q: any) => ({
      ...q.question,
      score: q.score || 5,
      examQuestionId: q.id,
    }))
  } catch { ElMessage.error('加载试卷失败') }
}

function typeLabel(type: string): string {
  const map: Record<string, string> = { single: '单选', multiple: '多选', true_false: '判断', fill_blank: '填空', essay: '问答' }
  return map[type] || type
}

function diffLabel(diff: string): string {
  const map: Record<string, string> = { easy: '简单', medium: '中等', hard: '困难' }
  return map[diff] || diff
}

async function openQuestionPicker() {
  try {
    const result = await getQuestionList({ page: 1, pageSize: 200 })
    availableQuestions.value = result.list.filter(
      (q: any) => !questions.value.find((sq: any) => sq.id === q.id)
    )
  } catch {
    availableQuestions.value = []
  }
  showQuestionPicker.value = true
}

function onPickerSelect(val: any[]) { pickerSelected.value = val }

function addSelectedQuestions() {
  const addedCount = pickerSelected.value.length
  pickerSelected.value.forEach((q: any) => {
    questions.value.push({ ...q, score: 5 })
  })
  showQuestionPicker.value = false
  pickerSelected.value = []
  ElMessage.success(`已添加 ${addedCount} 道题目`)
}

function removeQuestion(q: any) {
  questions.value = questions.value.filter((item: any) => item !== q)
}

async function handleRandomPreview() {
  // Simulate preview
  previewQuestions.value = [
    { content: '关于渐进多焦点镜片的适配要点有哪些？' },
    { content: '以下哪些是防蓝光镜片的特点？' },
    { content: '眼镜门店陈列的基本原则是什么？' },
  ]
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  if (form.type === 'manual' && questions.value.length === 0) {
    ElMessage.warning('请至少添加一道题目')
    return
  }

  submitting.value = true
  try {
    const params: any = {
      title: form.title,
      type: form.type,
      duration: form.duration,
      totalScore: form.totalScore,
      passScore: form.passScore,
      description: form.description,
      questionIds: questions.value.map((q: any) => q.id),
    }

    if (isEditing.value) {
      await updateExam(Number(route.params.id), params)
      ElMessage.success('更新成功')
    } else {
      await createExam(params)
      ElMessage.success('创建成功')
    }
  } catch { /* handled */ } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
.mb-4 { margin-bottom: 16px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-item {
  padding: 8px 0;
  font-size: 14px;
  color: #606266;
  border-bottom: 1px solid #f0f0f0;

  .preview-num { color: #409eff; font-weight: 600; }
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;

  .label { color: #909399; font-size: 13px; }
  .value { color: #303133; font-weight: 600; font-size: 14px; }
}

.diff-easy { color: #67c23a; }
.diff-medium { color: #e6a23c; }
.diff-hard { color: #f56c6c; }

.form-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
