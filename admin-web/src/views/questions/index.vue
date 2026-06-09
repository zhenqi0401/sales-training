<template>
  <div class="page-container">
    <div class="page-header">
      <h2>题目管理</h2>
      <p>管理题库中的题目，支持多种题型</p>
    </div>

    <div class="search-form">
      <el-input
        v-model="searchForm.keyword"
        placeholder="搜索题目内容"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="searchForm.categoryId"
        placeholder="选择分类"
        clearable
        style="width: 150px"
        @change="handleSearch"
      >
        <el-option v-for="cat in flatCategories" :key="cat.id" :label="cat.name" :value="cat.id" />
      </el-select>
      <el-select
        v-model="searchForm.type"
        placeholder="题目类型"
        clearable
        style="width: 130px"
        @change="handleSearch"
      >
        <el-option label="单选题" value="single" />
        <el-option label="多选题" value="multiple" />
        <el-option label="判断题" value="true_false" />
        <el-option label="填空题" value="fill_blank" />
        <el-option label="问答题" value="essay" />
      </el-select>
      <el-select
        v-model="searchForm.difficulty"
        placeholder="难度"
        clearable
        style="width: 110px"
        @change="handleSearch"
      >
        <el-option label="简单" value="easy" />
        <el-option label="中等" value="medium" />
        <el-option label="困难" value="hard" />
      </el-select>
      <el-input
        v-model="searchForm.tag"
        placeholder="标签"
        clearable
        style="width: 140px"
        @keyup.enter="handleSearch"
      />
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <div class="table-container">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="$router.push('/questions/edit')">
            <el-icon><Plus /></el-icon>新增题目
          </el-button>
          <el-button @click="$router.push('/questions/ai-generate')">
            <el-icon><MagicStick /></el-icon>AI出题
          </el-button>
          <el-button @click="downloadTemplate">
            <el-icon><Download /></el-icon>下载模板
          </el-button>
          <el-button @click="triggerImport">
            <el-icon><Upload /></el-icon>批量导入
          </el-button>
          <el-button :disabled="selectedIds.length === 0" type="danger" plain @click="batchDelete">
            <el-icon><Delete /></el-icon>批量删除
          </el-button>
          <input
            ref="fileInputRef"
            class="hidden-file-input"
            type="file"
            accept=".xlsx,.xls"
            @change="handleImportFile"
          />
        </div>
        <div class="toolbar-right">
          <span class="table-total">共 {{ total }} 道题目</span>
        </div>
      </div>

      <el-table
        ref="tableRef"
        :data="questionList"
        stripe
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="content" label="题目内容" min-width="280" show-overflow-tooltip />
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.type)" size="small">{{ typeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="难度" width="80" align="center">
          <template #default="{ row }">
            <span :class="'difficulty-' + row.difficulty">{{ diffLabel(row.difficulty) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="140">
          <template #default="{ row }">{{ categoryLabel(row.categoryId, row.categoryName) }}</template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" width="190">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-item">
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'active'" type="success" size="small">启用</el-tag>
            <el-tag v-else type="info" size="small">禁用</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openPreview(row)">预览</el-button>
            <el-button text type="primary" size="small" @click="$router.push(`/questions/edit/${row.id}`)">编辑</el-button>
            <el-popconfirm teleported :persistent="false" popper-class="delete-popconfirm" title="确定删除此题目吗？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button text type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="getList"
          @current-change="getList"
        />
      </div>
    </div>

    <el-dialog v-model="previewVisible" title="题目预览和测试" width="680px">
      <div v-if="previewQuestion" class="preview-body">
        <div class="preview-meta">
          <el-tag :type="typeTag(previewQuestion.type)" size="small">{{ typeLabel(previewQuestion.type) }}</el-tag>
          <span :class="'difficulty-' + previewQuestion.difficulty">{{ diffLabel(previewQuestion.difficulty) }}</span>
          <span>{{ categoryLabel(previewQuestion.categoryId, previewQuestion.categoryName) }}</span>
        </div>
        <div class="preview-content">{{ previewQuestion.content }}</div>
        <div v-if="previewQuestion.tags.length > 0" class="preview-tags">
          <el-tag v-for="tag in previewQuestion.tags" :key="tag" size="small">{{ tag }}</el-tag>
        </div>

        <div v-if="hasOptions(previewQuestion)" class="preview-options">
          <div v-for="option in previewQuestion.options" :key="option.label" class="preview-option">
            <span>{{ option.label }}.</span>
            <span>{{ option.value }}</span>
          </div>
        </div>

        <el-form label-width="88px" class="test-form">
          <el-form-item label="测试答案">
            <el-select
              v-if="previewQuestion.type === 'single'"
              v-model="testTextAnswer"
              placeholder="选择答案"
              style="width: 220px"
            >
              <el-option v-for="option in previewQuestion.options" :key="option.label" :label="option.label" :value="option.label" />
            </el-select>
            <el-checkbox-group v-else-if="previewQuestion.type === 'multiple'" v-model="testArrayAnswer">
              <el-checkbox v-for="option in previewQuestion.options" :key="option.label" :label="option.label" :value="option.label">
                {{ option.label }}
              </el-checkbox>
            </el-checkbox-group>
            <el-radio-group v-else-if="previewQuestion.type === 'true_false'" v-model="testTextAnswer">
              <el-radio value="正确">正确</el-radio>
              <el-radio value="错误">错误</el-radio>
            </el-radio-group>
            <el-input
              v-else
              v-model="testTextAnswer"
              type="textarea"
              :rows="2"
              placeholder="输入答案"
            />
          </el-form-item>
        </el-form>

        <el-alert
          v-if="testSubmitted"
          :title="testPassed ? '测试通过' : '答案不匹配'"
          :type="testPassed ? 'success' : 'warning'"
          show-icon
          :closable="false"
        />
        <div class="answer-block">
          <div><strong>正确答案：</strong>{{ answerText(previewQuestion.answer) }}</div>
          <div v-if="previewQuestion.explanation"><strong>解析：</strong>{{ previewQuestion.explanation }}</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" @click="submitPreviewTest">测试答案</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download, MagicStick, Plus, Upload } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import { getQuestionList, deleteQuestion, batchDeleteQuestions, importQuestions } from '@/api/questions'
import { getCategoryList } from '@/api/categories'
import type { Category, Difficulty, Question, QuestionOption, QuestionType } from '@/types'

type SearchForm = {
  keyword: string
  categoryId?: number
  type?: QuestionType
  difficulty?: Difficulty
  tag: string
}

type ImportRow = Record<string, string | number | undefined>

const loading = ref(false)
const importing = ref(false)
const questionList = ref<Question[]>([])
const categories = ref<Category[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const selectedIds = ref<number[]>([])
const tableRef = ref<any>()
const fileInputRef = ref<HTMLInputElement>()
const previewVisible = ref(false)
const previewQuestion = ref<Question | null>(null)
const testTextAnswer = ref('')
const testArrayAnswer = ref<string[]>([])
const testSubmitted = ref(false)

const searchForm = reactive<SearchForm>({
  keyword: '',
  categoryId: undefined,
  type: undefined,
  difficulty: undefined,
  tag: '',
})

const flatCategories = computed(() => flattenCategories(categories.value))
const testPassed = computed(() => {
  if (!previewQuestion.value) return false
  const answer = previewQuestion.value.type === 'multiple' ? testArrayAnswer.value : testTextAnswer.value
  return normalizeAnswer(answer) === normalizeAnswer(previewQuestion.value.answer)
})

onMounted(() => {
  getCategories()
  getList()
})

async function getCategories() {
  try {
    categories.value = await getCategoryList()
  } catch {
    categories.value = []
  }
}

async function getList() {
  loading.value = true
  try {
    const result = await getQuestionList({
      page: currentPage.value,
      pageSize: pageSize.value,
      ...searchForm,
    })
    questionList.value = result.list
    total.value = result.total
  } catch {
    questionList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  getList()
}

function resetSearch() {
  searchForm.keyword = ''
  searchForm.categoryId = undefined
  searchForm.type = undefined
  searchForm.difficulty = undefined
  searchForm.tag = ''
  currentPage.value = 1
  getList()
}

function handleSelectionChange(rows: Question[]) {
  selectedIds.value = rows.map((row) => row.id)
}

async function handleDelete(id: number) {
  try {
    await deleteQuestion(id)
    ElMessage.success('删除成功')
    await getList()
  } catch {
    /* handled by interceptor */
  }
}

async function batchDelete() {
  if (selectedIds.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedIds.value.length} 道题目吗？`,
      '确认删除',
      {
        appendTo: document.body,
        customClass: 'confirm-dialog',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        center: true,
        draggable: false,
      },
    )
    await batchDeleteQuestions(selectedIds.value)
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    tableRef.value?.clearSelection()
    await getList()
  } catch {
    /* cancelled or handled by interceptor */
  }
}

function downloadTemplate() {
  const rows = [
    {
      题目内容: '顾客试戴镜架时，销售顾问首先应该关注什么？',
      题型: 'single',
      难度: 'medium',
      分类ID: flatCategories.value[0]?.id ?? '',
      选项A: '脸型适配和佩戴舒适度',
      选项B: '只推荐价格最高的款式',
      选项C: '立即催促顾客付款',
      选项D: '忽略顾客反馈',
      选项E: '',
      选项F: '',
      正确答案: 'A',
      解析: '试戴环节应先判断适配度和舒适度，再结合预算推荐。',
      标签: '试戴,服务流程',
    },
    {
      题目内容: '镜片推荐时需要结合顾客的用眼场景。',
      题型: 'true_false',
      难度: 'easy',
      分类ID: flatCategories.value[0]?.id ?? '',
      选项A: '正确',
      选项B: '错误',
      选项C: '',
      选项D: '',
      选项E: '',
      选项F: '',
      正确答案: '正确',
      解析: '用眼场景是镜片功能推荐的关键依据。',
      标签: '镜片,需求分析',
    },
  ]
  const sheet = XLSX.utils.json_to_sheet(rows)
  sheet['!cols'] = [
    { wch: 38 },
    { wch: 12 },
    { wch: 12 },
    { wch: 10 },
    { wch: 26 },
    { wch: 26 },
    { wch: 26 },
    { wch: 26 },
    { wch: 18 },
    { wch: 18 },
    { wch: 16 },
    { wch: 36 },
    { wch: 22 },
  ]
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, sheet, '题目模板')
  XLSX.writeFile(workbook, '题目导入模板.xlsx')
}

function triggerImport() {
  if (importing.value) return
  fileInputRef.value?.click()
}

async function handleImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  importing.value = true
  try {
    const buffer = await file.arrayBuffer()
    const workbook = XLSX.read(buffer)
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    const rows = XLSX.utils.sheet_to_json<ImportRow>(sheet, { defval: '' })
    const questions = rows.map(parseImportRow).filter((item): item is Partial<Question> => Boolean(item))
    if (questions.length === 0) {
      ElMessage.warning('没有可导入的题目')
      return
    }

    const result = await importQuestions(questions)
    ElMessage.success(result.message)
    currentPage.value = 1
    await getList()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入失败')
  } finally {
    importing.value = false
  }
}

function parseImportRow(row: ImportRow): Partial<Question> | null {
  const content = normalizeCell(row['题目内容'])
  const answer = normalizeCell(row['正确答案'])
  if (!content || !answer) return null

  const type = parseType(normalizeCell(row['题型']))
  const categoryId = Number(normalizeCell(row['分类ID'])) || undefined
  const options = buildOptions(row, type)

  return {
    content,
    type,
    difficulty: parseDifficulty(normalizeCell(row['难度'])),
    categoryId,
    options,
    answer: type === 'multiple'
      ? answer.split(/[,\s，、]+/).map((item) => item.trim()).filter(Boolean)
      : answer,
    explanation: normalizeCell(row['解析']),
    tags: normalizeCell(row['标签']).split(/[,\s，、]+/).map((item) => item.trim()).filter(Boolean),
  }
}

function buildOptions(row: ImportRow, type: QuestionType): QuestionOption[] {
  if (type === 'true_false') {
    return [
      { label: 'A', value: normalizeCell(row['选项A']) || '正确' },
      { label: 'B', value: normalizeCell(row['选项B']) || '错误' },
    ]
  }
  if (!['single', 'multiple'].includes(type)) return []

  return ['A', 'B', 'C', 'D', 'E', 'F']
    .map((label) => ({ label, value: normalizeCell(row[`选项${label}`]) }))
    .filter((option) => option.value)
}

function openPreview(question: any) {
  previewQuestion.value = question as Question
  testTextAnswer.value = ''
  testArrayAnswer.value = []
  testSubmitted.value = false
  previewVisible.value = true
}

function submitPreviewTest() {
  testSubmitted.value = true
}

function hasOptions(question: Question) {
  return ['single', 'multiple', 'true_false'].includes(question.type) && question.options.length > 0
}

function flattenCategories(items: Category[]): Category[] {
  return items.flatMap((item) => [item, ...flattenCategories(item.children ?? [])])
}

function categoryLabel(id?: number | null, fallback?: string): string {
  if (fallback) return fallback
  return flatCategories.value.find((cat) => cat.id === id)?.name ?? '-'
}

function normalizeCell(value: string | number | undefined): string {
  return String(value ?? '').trim()
}

function parseType(value: string): QuestionType {
  const map: Record<string, QuestionType> = {
    single: 'single',
    单选: 'single',
    单选题: 'single',
    multiple: 'multiple',
    多选: 'multiple',
    多选题: 'multiple',
    true_false: 'true_false',
    判断: 'true_false',
    判断题: 'true_false',
    fill_blank: 'fill_blank',
    填空: 'fill_blank',
    填空题: 'fill_blank',
    essay: 'essay',
    问答: 'essay',
    问答题: 'essay',
  }
  return map[value] ?? 'single'
}

function parseDifficulty(value: string): Difficulty {
  const map: Record<string, Difficulty> = {
    easy: 'easy',
    简单: 'easy',
    '1': 'easy',
    '2': 'easy',
    medium: 'medium',
    中等: 'medium',
    '3': 'medium',
    hard: 'hard',
    困难: 'hard',
    '4': 'hard',
    '5': 'hard',
  }
  return map[value] ?? 'medium'
}

function normalizeAnswer(answer: string | string[]): string {
  const values = Array.isArray(answer) ? answer : String(answer).split(',')
  return values.map((item) => item.trim()).filter(Boolean).sort().join(',')
}

function answerText(answer: string | string[]): string {
  return Array.isArray(answer) ? answer.join('、') : answer
}

function typeLabel(type: string): string {
  const map: Record<string, string> = { single: '单选', multiple: '多选', true_false: '判断', fill_blank: '填空', essay: '问答' }
  return map[type] || type
}

function typeTag(type: string): 'success' | 'warning' | 'info' | 'primary' | 'danger' | undefined {
  const map: Record<string, 'success' | 'warning' | 'info' | 'primary' | 'danger' | undefined> = {
    single: undefined,
    multiple: 'warning',
    true_false: 'info',
    fill_blank: 'success',
    essay: 'primary',
  }
  return map[type]
}

function diffLabel(diff: string): string {
  const map: Record<string, string> = { easy: '简单', medium: '中等', hard: '困难' }
  return map[diff] || diff
}
</script>

<style scoped lang="scss">
.tag-item {
  margin-right: 4px;
  margin-bottom: 2px;
}

.difficulty-easy { color: #67c23a; }
.difficulty-medium { color: #e6a23c; }
.difficulty-hard { color: #f56c6c; }

.hidden-file-input {
  display: none;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.preview-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.preview-meta,
.preview-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.preview-content {
  font-size: 16px;
  line-height: 1.7;
  color: #303133;
}

.preview-options {
  display: grid;
  gap: 8px;
}

.preview-option {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 8px;
  line-height: 1.6;
}

.test-form {
  margin-top: 4px;
}

.answer-block {
  display: grid;
  gap: 6px;
  color: #606266;
  line-height: 1.6;
}
</style>
