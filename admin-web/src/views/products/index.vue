<template>
  <div class="page-container">
    <div class="page-header">
      <h2>产品知识</h2>
      <p>管理产品知识库，包含眼镜产品参数、卖点、使用说明等</p>
    </div>

    <div class="search-form">
      <el-input
        v-model="searchForm.keyword"
        placeholder="搜索产品名称"
        clearable
        style="width: 200px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="searchForm.category"
        placeholder="产品分类"
        clearable
        style="width: 160px"
        @change="handleSearch"
      >
        <el-option
          v-for="cat in categoryOptions"
          :key="cat.code"
          :label="`${cat.name} (${cat.count})`"
          :value="cat.code"
        />
      </el-select>
      <el-select
        v-model="searchForm.brand"
        placeholder="品牌"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option
          v-for="brand in brandOptions"
          :key="brand"
          :label="brand"
          :value="brand"
        />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <div class="table-container">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>新增产品
          </el-button>
        </div>
      </div>

      <el-table :data="productList" stripe v-loading="loading">
        <el-table-column label="封面" width="80">
          <template #default="{ row }">
            <el-image :src="row.coverUrl || ''" style="width: 48px; height: 48px; border-radius: 4px" fit="cover">
              <template #error><div class="cover-placeholder"><el-icon :size="20"><Goods /></el-icon></div></template>
            </el-image>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="产品名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="分类" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ categoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="brand" label="品牌" width="100" align="center" />
        <el-table-column label="状态" width="90" align="center">
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
            <el-button text type="primary" size="small" @click="previewProduct(row)">预览</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
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
      :title="isEditingProduct ? '编辑产品' : '新增产品'"
      width="750px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="产品名称" prop="title">
              <el-input v-model="form.title" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="分类" prop="category">
              <el-select v-model="form.category" style="width: 100%">
                <el-option
                  v-for="cat in categoryOptions"
                  :key="cat.code"
                  :label="cat.name"
                  :value="cat.code"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="品牌">
              <el-input v-model="form.brand" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="产品内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="10" placeholder="产品详细说明，支持 Markdown 格式" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple allow-create filterable placeholder="输入标签后按回车" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="published">发布</el-radio>
            <el-radio value="draft">草稿</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- Preview -->
    <el-dialog v-model="previewVisible" title="产品预览" width="700px">
      <div class="preview-content">
        <el-row :gutter="16" align="middle">
          <el-col :span="6">
            <el-image :src="previewData.coverUrl || ''" style="width: 120px; height: 120px; border-radius: 8px" fit="cover">
              <template #error><div class="preview-placeholder-img"><el-icon :size="32"><Goods /></el-icon></div></template>
            </el-image>
          </el-col>
          <el-col :span="18">
            <h3>{{ previewData.title }}</h3>
            <div class="preview-meta">
              <el-tag size="small">{{ categoryLabel(previewData.category) }}</el-tag>
              <span v-if="previewData.brand" style="margin-left: 8px; color: #909399">品牌：{{ previewData.brand }}</span>
            </div>
          </el-col>
        </el-row>
        <el-divider />
        <div class="preview-body">{{ previewData.content }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { confirmDanger } from '@/utils/confirm'
import type { FormInstance, FormRules } from 'element-plus'
import { getProductList, createProduct, updateProduct, deleteProduct, getProductCategoryOptions } from '@/api/products'
import type { ProductKnowledge } from '@/types'
import type { ProductCategoryOption } from '@/api/products'

const loading = ref(false)
const productList = ref<ProductKnowledge[]>([])
const categoryOptions = ref<ProductCategoryOption[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const dialogVisible = ref(false)
const isEditingProduct = ref(false)
const editingId = ref<number | null>(null)

// Preview
const previewVisible = ref(false)
const previewData = ref<any>({})

const searchForm = reactive({
  keyword: '',
  category: undefined as string | undefined,
  brand: undefined as string | undefined,
})

const brandOptions = computed(() => {
  return Array.from(new Set(productList.value.map(item => item.brand).filter(Boolean))) as string[]
})

const form = reactive({
  title: '',
  category: 'lens',
  brand: '',
  content: '',
  tags: [] as string[],
  status: 'draft',
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入产品名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入产品内容', trigger: 'blur' }],
}

onMounted(() => {
  getCategories()
  getList()
})

async function getCategories() {
  try {
    categoryOptions.value = await getProductCategoryOptions()
  } catch {
    categoryOptions.value = []
  }
}

async function getList() {
  loading.value = true
  try {
    const result = await getProductList({ page: currentPage.value, pageSize: pageSize.value, ...searchForm })
    productList.value = result.list
    total.value = result.total
  } catch { productList.value = [] } finally { loading.value = false }
}

function handleSearch() { currentPage.value = 1; getList() }
function resetSearch() { searchForm.keyword = ''; searchForm.category = undefined; searchForm.brand = undefined; currentPage.value = 1; getList() }

function openDialog(row?: any) {
  if (row) {
    isEditingProduct.value = true
    editingId.value = row.id
    form.title = row.title
    form.category = row.category
    form.brand = row.brand || ''
    form.content = row.content
    form.tags = row.tags
    form.status = row.status
  } else {
    isEditingProduct.value = false
    editingId.value = null
    form.title = ''
    form.category = categoryOptions.value[0]?.code || 'lens'
    form.brand = ''
    form.content = ''
    form.tags = []
    form.status = 'draft'
  }
  dialogVisible.value = true
}

function previewProduct(row: any) {
  previewData.value = row
  previewVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEditingProduct.value && editingId.value) {
      await updateProduct(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createProduct(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    getList()
  } catch { /* handled */ } finally { submitting.value = false }
}

async function handleDelete(id: number) {
  try { await confirmDanger('确定删除此产品吗？')
    await deleteProduct(id); ElMessage.success('删除成功'); getList() } catch { /* handled */ }
}

function categoryLabel(cat: string): string {
  return categoryOptions.value.find(item => item.code === cat)?.name || cat
}
</script>

<style scoped lang="scss">
.pagination-wrap { margin-top: 20px; display: flex; justify-content: flex-end; }

.cover-placeholder {
  width: 48px; height: 48px; background: #f5f7fa; border-radius: 4px;
  display: flex; align-items: center; justify-content: center; color: #c0c4cc;
}

.preview-content {
  h3 { margin: 0 0 8px; color: #303133; }
  .preview-meta { margin-bottom: 8px; }
  .preview-body { font-size: 15px; line-height: 1.8; color: #303133; white-space: pre-wrap; }
}

.preview-placeholder-img {
  width: 120px; height: 120px; background: #f5f7fa; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; color: #c0c4cc;
}
</style>
