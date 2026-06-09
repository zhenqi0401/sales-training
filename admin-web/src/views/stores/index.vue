<template>
  <div class="page-container">
    <div class="page-header">
      <h2>门店管理</h2>
      <p>管理系统中的门店信息</p>
    </div>

    <div class="search-form">
      <el-input
        v-model="searchForm.keyword"
        placeholder="搜索门店名称/编码"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="searchForm.status"
        placeholder="状态"
        clearable
        style="width: 120px"
        @change="handleSearch"
      >
        <el-option label="营业中" :value="1" />
        <el-option label="已停业" :value="0" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <div class="table-container">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>新增门店
          </el-button>
        </div>
      </div>

      <el-table :data="storeList" stripe v-loading="loading">
        <el-table-column prop="name" label="门店名称" min-width="200" />
        <el-table-column prop="code" label="门店编码" width="140" />
        <el-table-column prop="address" label="地址" min-width="250" show-overflow-tooltip />
        <el-table-column prop="phone" label="联系电话" width="140" />
        <el-table-column prop="manager" label="负责人" width="120" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.status === 1"
              @change="(val) => handleToggleStatus(row as Store, Boolean(val))"
            />
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openDialog(row as Store)">编辑</el-button>
            <el-popconfirm teleported :persistent="false" popper-class="delete-popconfirm" title="确定删除此门店吗？" @confirm="handleDelete(row.id)">
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

    <!-- Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditingStore ? '编辑门店' : '新增门店'"
      width="550px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="门店名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="门店编码" prop="code">
              <el-input v-model="form.code" :disabled="isEditingStore" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="门店地址">
          <el-input v-model="form.address" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="form.phone" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="负责人">
              <el-input v-model="form.manager" />
            </el-form-item>
          </el-col>
        </el-row>
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
import { getStoreList, createStore, updateStore, deleteStore, toggleStoreStatus } from '@/api/stores'
import type { Store } from '@/types'

const loading = ref(false)
const storeList = ref<Store[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const dialogVisible = ref(false)
const isEditingStore = ref(false)
const editingId = ref<number | null>(null)

const searchForm = reactive({
  keyword: '',
  status: undefined as number | undefined,
})

const form = reactive({
  name: '',
  code: '',
  address: '',
  phone: '',
  manager: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入门店名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入门店编码', trigger: 'blur' }],
}

onMounted(() => getList())

async function getList() {
  loading.value = true
  try {
    const result = await getStoreList({ page: currentPage.value, pageSize: pageSize.value, ...searchForm })
    storeList.value = result.list
    total.value = result.total
  } catch { storeList.value = [] } finally { loading.value = false }
}

function handleSearch() { currentPage.value = 1; getList() }
function resetSearch() { searchForm.keyword = ''; searchForm.status = undefined; currentPage.value = 1; getList() }

function openDialog(row?: Store) {
  if (row) {
    isEditingStore.value = true
    editingId.value = row.id
    form.name = row.name
    form.code = row.code
    form.address = row.address || ''
    form.phone = row.phone || ''
    form.manager = row.manager || ''
  } else {
    isEditingStore.value = false
    editingId.value = null
    form.name = ''
    form.code = ''
    form.address = ''
    form.phone = ''
    form.manager = ''
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEditingStore.value && editingId.value) {
      await updateStore(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createStore(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    getList()
  } catch { /* handled */ } finally { submitting.value = false }
}

async function handleToggleStatus(row: Store, enabled: boolean) {
  try { await toggleStoreStatus(row.id, enabled ? 1 : 0); row.status = enabled ? 1 : 0; ElMessage.success(enabled ? '已启用' : '已停业') }
  catch { ElMessage.error('操作失败') }
}

async function handleDelete(id: number) {
  try { await deleteStore(id); ElMessage.success('删除成功'); getList() } catch { /* handled */ }
}
</script>

<style scoped lang="scss">
.pagination-wrap { margin-top: 20px; display: flex; justify-content: flex-end; }
</style>
