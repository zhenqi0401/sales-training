<template>
  <div class="page-container">
    <div class="page-header">
      <h2>分类管理</h2>
      <p>管理课程分类，支持多级分类结构</p>
    </div>

    <el-card shadow="hover">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>新增分类
          </el-button>
          <el-button @click="refreshTree">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>
      </div>

      <el-table
        :data="categoryTree"
        row-key="id"
        :tree-props="{ children: 'children' }"
        default-expand-all
        stripe
        v-loading="loading"
      >
        <el-table-column prop="name" label="分类名称" min-width="200">
          <template #default="{ row }">
            <div class="category-name">
              <el-icon v-if="row.children && row.children.length" color="#409eff"><Folder /></el-icon>
              <el-icon v-else color="#e6a23c"><Document /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="videoCount" label="视频数量" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.videoCount || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort" label="排序" width="100" align="center" />
        <el-table-column prop="createdAt" label="创建时间" width="180">
          <template #default="{ row }">
            {{ row.createdAt || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button text type="primary" size="small" @click="openDialog(undefined, row.id)">添加子分类</el-button>
            <el-popconfirm title="确定删除此分类吗？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button text type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑分类' : '新增分类'"
      width="500px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入分类名称" maxlength="20" />
        </el-form-item>
        <el-form-item label="上级分类" v-if="!form.parentId">
          <el-tree-select
            v-model="form.parentId"
            :data="categoryTree"
            :props="{ label: 'name', value: 'id', children: 'children' }"
            placeholder="不选则为顶级分类"
            clearable
            check-strictly
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getCategoryTree, createCategory, updateCategory, deleteCategory } from '@/api/categories'
import type { Category } from '@/types'

const loading = ref(false)
const submitting = ref(false)
const categoryTree = ref<Category[]>([])
const dialogVisible = ref(false)
const isEditing = ref(false)
const formRef = ref<FormInstance>()
const editingId = ref<number | null>(null)

const form = reactive({
  name: '',
  parentId: null as number | null,
  sort: 0,
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { min: 1, max: 20, message: '长度在 1 到 20 个字符', trigger: 'blur' },
  ],
}

onMounted(() => {
  refreshTree()
})

async function refreshTree() {
  loading.value = true
  try {
    categoryTree.value = await getCategoryTree()
  } catch {
    categoryTree.value = []
  } finally {
    loading.value = false
  }
}

function openDialog(row?: Category, parentId?: number) {
  if (row) {
    isEditing.value = true
    editingId.value = row.id
    form.name = row.name
    form.parentId = row.parentId
    form.sort = row.sort
  } else {
    isEditing.value = false
    editingId.value = null
    form.name = ''
    form.parentId = parentId || null
    form.sort = 0
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEditing.value && editingId.value) {
      await updateCategory(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createCategory(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    refreshTree()
  } catch {
    // Error handled by interceptor
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await deleteCategory(id)
    ElMessage.success('删除成功')
    refreshTree()
  } catch {
    // Error handled by interceptor
  }
}
</script>

<style scoped lang="scss">
.category-name {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
