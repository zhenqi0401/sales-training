<template>
  <div class="page-container">
    <div class="page-header">
      <h2>话术管理</h2>
      <p>管理销售话术内容，帮助销售人员提升沟通技巧</p>
    </div>

    <div class="search-form">
      <el-input
        v-model="searchForm.keyword"
        placeholder="搜索话术标题"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="searchForm.category"
        placeholder="话术分类"
        clearable
        style="width: 160px"
        @change="handleSearch"
      >
        <el-option
          v-for="cat in categoryOptions"
          :key="cat.value"
          :label="`${cat.label} (${cat.count})`"
          :value="cat.value"
        />
      </el-select>
      <el-select
        v-model="searchForm.status"
        placeholder="状态"
        clearable
        style="width: 120px"
        @change="handleSearch"
      >
        <el-option label="已发布" value="published" />
        <el-option label="草稿" value="draft" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <div class="table-container">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>新增话术
          </el-button>
        </div>
      </div>

      <el-table :data="scriptList" stripe v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="分类" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ categoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'published'" type="success" size="small">已发布</el-tag>
            <el-tag v-else type="info" size="small">草稿</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tags" label="标签" width="200">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" style="margin-right: 4px">{{ tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button text type="primary" size="small" @click="previewScript(row)">预览</el-button>
            <el-popconfirm title="确定删除吗？" @confirm="handleDelete(row.id)">
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
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="getList"
          @current-change="getList"
        />
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditingScript ? '编辑话术' : '新增话术'"
      width="700px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="话术标题" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类" prop="category">
              <el-select v-model="form.category" style="width: 100%">
                <el-option
                  v-for="cat in categoryOptions"
                  :key="cat.value"
                  :label="cat.label"
                  :value="cat.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-radio-group v-model="form.status">
                <el-radio value="published">发布</el-radio>
                <el-radio value="draft">草稿</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="话术内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="10"
            placeholder="请输入话术内容，支持 Markdown 格式"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple allow-create filterable placeholder="输入标签后按回车" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- Preview Dialog -->
    <el-dialog v-model="previewVisible" title="话术预览" width="700px">
      <div class="preview-content">
        <h3>{{ previewData.title }}</h3>
        <div class="preview-meta">
          <el-tag size="small">{{ categoryLabel(previewData.category) }}</el-tag>
          <el-tag v-for="tag in previewData.tags" :key="tag" size="small" style="margin-left: 6px">{{ tag }}</el-tag>
        </div>
        <el-divider />
        <div class="preview-body">{{ previewData.content }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getScriptList, createScript, updateScript, deleteScript, getScriptCategoryOptions } from '@/api/scripts'
import type { SalesScript } from '@/types'
import type { ScriptCategoryOption } from '@/api/scripts'

const loading = ref(false)
const scriptList = ref<SalesScript[]>([])
const categoryOptions = ref<ScriptCategoryOption[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const dialogVisible = ref(false)
const isEditingScript = ref(false)
const editingId = ref<number | null>(null)

// Preview
const previewVisible = ref(false)
const previewData = ref<any>({})

const searchForm = reactive({
  keyword: '',
  category: undefined as string | undefined,
  status: undefined as string | undefined,
})

const form = reactive({
  title: '',
  category: 'product',
  content: '',
  tags: [] as string[],
  status: 'draft',
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入话术内容', trigger: 'blur' }],
}

onMounted(() => {
  getCategories()
  getList()
})

async function getCategories() {
  try {
    categoryOptions.value = await getScriptCategoryOptions()
  } catch {
    categoryOptions.value = []
  }
}

async function getList() {
  loading.value = true
  try {
    const result = await getScriptList({ page: currentPage.value, pageSize: pageSize.value, ...searchForm })
    scriptList.value = result.list
    total.value = result.total
  } catch { scriptList.value = [] } finally { loading.value = false }
}

function handleSearch() { currentPage.value = 1; getList() }
function resetSearch() { searchForm.keyword = ''; searchForm.category = undefined; searchForm.status = undefined; currentPage.value = 1; getList() }

function openDialog(row?: any) {
  if (row) {
    isEditingScript.value = true
    editingId.value = row.id
    form.title = row.title
    form.category = row.category
    form.content = row.content
    form.tags = row.tags
    form.status = row.status
  } else {
    isEditingScript.value = false
    editingId.value = null
    form.title = ''
    form.category = categoryOptions.value[0]?.value || 'product'
    form.content = ''
    form.tags = []
    form.status = 'draft'
  }
  dialogVisible.value = true
}

function previewScript(row: any) {
  previewData.value = row
  previewVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEditingScript.value && editingId.value) {
      await updateScript(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createScript(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    getList()
  } catch { /* handled */ } finally { submitting.value = false }
}

async function handleDelete(id: number) {
  try { await deleteScript(id); ElMessage.success('删除成功'); getList() } catch { /* handled */ }
}

function categoryLabel(cat: string): string {
  return categoryOptions.value.find(item => item.value === cat)?.label || cat
}
</script>

<style scoped lang="scss">
.pagination-wrap { margin-top: 20px; display: flex; justify-content: flex-end; }

.preview-content {
  h3 { margin: 0 0 12px; color: #303133; }
  .preview-meta { margin-bottom: 8px; }
  .preview-body {
    font-size: 15px;
    line-height: 1.8;
    color: #303133;
    white-space: pre-wrap;
  }
}
</style>
