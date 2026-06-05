<template>
  <div class="page-container">
    <div class="page-header">
      <h2>题目管理</h2>
      <p>管理题库中的题目，支持多种题型</p>
    </div>

    <!-- Search Form -->
    <div class="search-form">
      <el-input
        v-model="searchForm.keyword"
        placeholder="搜索题目内容"
        clearable
        style="width: 240px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="searchForm.categoryId"
        placeholder="选择分类"
        clearable
        style="width: 160px"
        @change="handleSearch"
      >
        <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
      </el-select>
      <el-select
        v-model="searchForm.type"
        placeholder="题目类型"
        clearable
        style="width: 140px"
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
        style="width: 120px"
        @change="handleSearch"
      >
        <el-option label="简单" value="easy" />
        <el-option label="中等" value="medium" />
        <el-option label="困难" value="hard" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <!-- Table -->
    <div class="table-container">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="$router.push('/questions/edit')">
            <el-icon><Plus /></el-icon>新增题目
          </el-button>
          <el-button @click="$router.push('/questions/ai-generate')">
            <el-icon><MagicStick /></el-icon>AI出题
          </el-button>
          <el-button :disabled="selectedIds.length === 0" type="danger" plain @click="batchDelete">
            <el-icon><Delete /></el-icon>批量删除
          </el-button>
        </div>
        <div class="toolbar-right">
          <span class="table-total">共 {{ total }} 道题目</span>
        </div>
      </div>

      <el-table
        :data="questionList"
        stripe
        v-loading="loading"
        @selection-change="(val: any[]) => selectedIds = val.map(v => v.id)"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="content" label="题目内容" min-width="300" show-overflow-tooltip />
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
        <el-table-column prop="categoryName" label="分类" width="120" />
        <el-table-column prop="tags" label="标签" width="200">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" style="margin-right: 4px; margin-bottom: 2px">
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
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="$router.push(`/questions/edit/${row.id}`)">编辑</el-button>
            <el-popconfirm title="确定删除此题目吗？" @confirm="handleDelete(row.id)">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getQuestionList, deleteQuestion, batchDeleteQuestions } from '@/api/questions'
import { getCategoryList } from '@/api/categories'
import type { Question, Category } from '@/types'

const loading = ref(false)
const questionList = ref<Question[]>([])
const categories = ref<Category[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const selectedIds = ref<number[]>([])

const searchForm = reactive({
  keyword: '',
  categoryId: undefined as number | undefined,
  type: undefined as string | undefined,
  difficulty: undefined as string | undefined,
})

onMounted(() => {
  getCategories()
  getList()
})

async function getCategories() {
  try {
    categories.value = await getCategoryList()
  } catch { categories.value = [] }
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
  currentPage.value = 1
  getList()
}

async function handleDelete(id: number) {
  try {
    await deleteQuestion(id)
    ElMessage.success('删除成功')
    getList()
  } catch { /* handled by interceptor */ }
}

async function batchDelete() {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 道题目吗？`, '确认删除')
    await batchDeleteQuestions(selectedIds.value)
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    getList()
  } catch { /* cancelled or error */ }
}

function typeLabel(type: string): string {
  const map: Record<string, string> = { single: '单选', multiple: '多选', true_false: '判断', fill_blank: '填空', essay: '问答' }
  return map[type] || type
}

function typeTag(type: string): string {
  const map: Record<string, string> = { single: '', multiple: 'warning', true_false: 'info', fill_blank: 'success', essay: 'primary' }
  return map[type] || ''
}

function diffLabel(diff: string): string {
  const map: Record<string, string> = { easy: '简单', medium: '中等', hard: '困难' }
  return map[diff] || diff
}
</script>

<style scoped lang="scss">
.difficulty-easy { color: #67c23a; }
.difficulty-medium { color: #e6a23c; }
.difficulty-hard { color: #f56c6c; }

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
