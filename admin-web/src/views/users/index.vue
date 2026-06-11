<template>
  <div class="page-container">
    <div class="page-header">
      <h2>用户管理</h2>
      <p>管理所有管理员和学员账号</p>
    </div>

    <div class="search-form">
      <el-input
        v-model="searchForm.keyword"
        placeholder="搜索用户名/姓名"
        clearable
        style="width: 200px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="searchForm.role"
        placeholder="角色"
        clearable
        style="width: 130px"
        @change="handleSearch"
      >
        <el-option label="管理员" value="admin" />
        <el-option label="培训师" value="trainer" />
        <el-option label="学员" value="student" />
      </el-select>
      <el-select
        v-model="searchForm.status"
        placeholder="状态"
        clearable
        style="width: 120px"
        @change="handleSearch"
      >
        <el-option label="启用" :value="1" />
        <el-option label="禁用" :value="0" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <div class="table-container">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>新增用户
          </el-button>
          <el-button @click="showImportDialog = true">
            <el-icon><Upload /></el-icon>批量导入
          </el-button>
        </div>
        <div class="toolbar-right">
          <span>共 {{ total }} 人</span>
        </div>
      </div>

      <el-table :data="userList" stripe v-loading="loading">
        <el-table-column label="头像" width="60" align="center">
          <template #default="{ row }">
            <el-avatar :size="36" :src="row.avatar" :icon="'UserFilled'" />
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="realName" label="姓名" width="120" />
        <el-table-column label="角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.role === 'admin'" type="danger" size="small">管理员</el-tag>
            <el-tag v-else-if="row.role === 'trainer'" type="warning" size="small">培训师</el-tag>
            <el-tag v-else type="primary" size="small">学员</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="storeName" label="所属门店" width="140" />
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.status === 1"
              :loading="row._statusLoading"
              @change="(val) => handleToggleStatus(row as UserInfo, Boolean(val))"
            />
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="注册时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="$router.push(`/users/detail/${row.id}`)">详情</el-button>
            <el-button text type="primary" size="small" @click="openEditDialog(row as UserInfo)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
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

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditingUser ? '编辑用户' : '新增用户'"
      width="600px"
    >
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="userForm.username" :disabled="isEditingUser" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名" prop="realName">
              <el-input v-model="userForm.realName" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16" v-if="!isEditingUser">
          <el-col :span="12">
            <el-form-item label="密码" prop="password">
              <el-input v-model="userForm.password" type="password" show-password />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色" prop="role">
              <el-select v-model="userForm.role" style="width: 100%">
                <el-option label="管理员" value="admin" />
                <el-option label="培训师" value="trainer" />
                <el-option label="学员" value="student" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="userForm.phone" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="userForm.email" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="所属门店">
          <el-select v-model="userForm.storeId" clearable style="width: 100%">
            <el-option v-for="s in stores" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="userSubmitting" @click="handleUserSubmit">确认</el-button>
      </template>
    </el-dialog>

    <!-- Import Dialog -->
    <el-dialog v-model="showImportDialog" title="批量导入用户" width="500px">
      <div class="import-tip">
        <p>请上传包含用户信息的 Excel 文件（.xlsx 或 .xls）</p>
        <p class="import-format">格式要求：用户名、密码、姓名、角色（admin/trainer/student）</p>
      </div>
      <el-upload
        drag
        :auto-upload="false"
        :on-change="handleImportFile"
        accept=".xlsx,.xls"
        style="margin-top: 16px"
      >
        <el-icon class="upload-icon" :size="40"><UploadFilled /></el-icon>
        <div class="upload-text">
          将文件拖拽到此处，或<em>点击选择文件</em>
        </div>
      </el-upload>
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!importFile" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { confirmDanger } from '@/utils/confirm'
import type { FormInstance, FormRules } from 'element-plus'
import { getUserList, createUser, updateUser, deleteUser, toggleUserStatus } from '@/api/users'
import { getAllStores } from '@/api/stores'
import type { UserInfo, Store } from '@/types'

const loading = ref(false)
const userList = ref<UserInfo[]>([])
const stores = ref<Store[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const searchForm = reactive({
  keyword: '',
  role: undefined as string | undefined,
  status: undefined as number | undefined,
})

// Dialog state
const dialogVisible = ref(false)
const isEditingUser = ref(false)
const editingUserId = ref<number | null>(null)
const userSubmitting = ref(false)
const userFormRef = ref<FormInstance>()

const userForm = reactive({
  username: '',
  realName: '',
  password: '',
  role: 'student',
  phone: '',
  email: '',
  storeId: null as number | null,
})

const userRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  realName: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '请输入 11 位手机号', trigger: 'blur' },
  ],
}

// Import state
const showImportDialog = ref(false)
const importFile = ref<File | null>(null)

onMounted(() => {
  getList()
  loadStores()
})

async function loadStores() {
  try { stores.value = (await getAllStores()) || [] } catch { stores.value = [] }
}

async function getList() {
  loading.value = true
  try {
    const result = await getUserList({
      page: currentPage.value,
      pageSize: pageSize.value,
      ...searchForm,
    })
    userList.value = result.list
    total.value = result.total
  } catch {
    userList.value = []
  } finally {
    loading.value = false
  }
}


function getApiErrorMessage(error: any, fallback: string) {
  const detail = error?.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg).filter(Boolean).join('；') || fallback
  }
  return typeof detail === 'string' ? detail : fallback
}

function handleSearch() { currentPage.value = 1; getList() }
function resetSearch() { searchForm.keyword = ''; searchForm.role = undefined; searchForm.status = undefined; currentPage.value = 1; getList() }

function openCreateDialog() {
  isEditingUser.value = false
  editingUserId.value = null
  userForm.username = ''
  userForm.realName = ''
  userForm.password = ''
  userForm.role = 'student'
  userForm.phone = ''
  userForm.email = ''
  userForm.storeId = null
  dialogVisible.value = true
}

function openEditDialog(row: UserInfo) {
  isEditingUser.value = true
  editingUserId.value = row.id
  userForm.username = row.username
  userForm.realName = row.realName
  userForm.password = ''
  userForm.role = row.role
  userForm.phone = row.phone || ''
  userForm.email = row.email || ''
  userForm.storeId = row.storeId || null
  dialogVisible.value = true
}

async function handleUserSubmit() {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return

  userSubmitting.value = true
  try {
    if (isEditingUser.value && editingUserId.value) {
      await updateUser(editingUserId.value, {
        realName: userForm.realName,
        phone: userForm.phone,
        email: userForm.email,
        storeId: userForm.storeId ?? undefined,
      })
      ElMessage.success('更新成功')
    } else {
      await createUser({
        username: userForm.username,
        realName: userForm.realName,
        password: userForm.password,
        role: userForm.role as any,
        phone: userForm.phone,
        email: userForm.email,
        storeId: userForm.storeId ?? undefined,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    getList()
  } catch (error: any) {
    ElMessage.error(getApiErrorMessage(error, '保存失败'))
  } finally {
    userSubmitting.value = false
  }
}

async function handleToggleStatus(row: UserInfo, enabled: boolean) {
  try {
    row._statusLoading = true
    await toggleUserStatus(row.id, enabled ? 1 : 0)
    row.status = enabled ? 1 : 0
    ElMessage.success(enabled ? '已启用' : '已禁用')
  } catch {
    ElMessage.error('操作失败')
  } finally {
    row._statusLoading = false
  }
}

async function handleDelete(id: number) {
  try {
    await confirmDanger('确定删除此用户吗？')
    await deleteUser(id)
    ElMessage.success('删除成功')
    getList()
  } catch { /* handled */ }
}

function handleImportFile(file: any) {
  importFile.value = file.raw
}

async function handleImport() {
  if (!importFile.value) return
  ElMessage.success('批量导入成功（演示模式）')
  showImportDialog.value = false
  importFile.value = null
  getList()
}
</script>

<style scoped lang="scss">
.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.import-tip {
  p { margin: 0 0 4px; font-size: 14px; color: #606266; }
  .import-format { font-size: 12px; color: #909399; }
}

.upload-icon { margin-bottom: 12px; }
.upload-text { font-size: 14px; color: #606266; em { color: #409eff; font-style: normal; } }
</style>
