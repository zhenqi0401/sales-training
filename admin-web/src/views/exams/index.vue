<template>
  <div class="page-container">
    <div class="page-header">
      <h2>试卷管理</h2>
      <p>管理考试试卷，支持手动组卷和自动组卷</p>
    </div>

    <div class="search-form">
      <el-input
        v-model="searchForm.keyword"
        placeholder="搜索试卷名称"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="searchForm.status"
        placeholder="选择状态"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option label="已发布" value="published" />
        <el-option label="草稿" value="draft" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <div class="table-container">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="$router.push('/exams/edit')">
            <el-icon><Plus /></el-icon>新增试卷
          </el-button>
        </div>
      </div>

      <el-table :data="examList" stripe v-loading="loading">
        <el-table-column prop="title" label="试卷名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="type" label="组卷方式" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === 'manual' ? 'primary' : row.type === 'random' ? 'success' : 'warning'" size="small">
              {{ row.type === 'manual' ? '手动组卷' : row.type === 'random' ? '随机组卷' : 'AI组卷' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="questionCount" label="题量" width="80" align="center" />
        <el-table-column prop="totalScore" label="总分" width="80" align="center" />
        <el-table-column prop="passScore" label="及格分" width="80" align="center" />
        <el-table-column prop="duration" label="时长(分钟)" width="100" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'published'" type="success" size="small">已发布</el-tag>
            <el-tag v-else-if="row.status === 'draft'" type="info" size="small">草稿</el-tag>
            <el-tag v-else type="danger" size="small">已关闭</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="$router.push(`/exams/edit/${row.id}`)">编辑</el-button>
            <el-button
              v-if="row.status === 'draft'"
              text
              type="success"
              size="small"
              @click="handlePublish(row.id)"
            >发布</el-button>
            <el-button
              v-if="row.status === 'published'"
              text
              type="danger"
              size="small"
              @click="handleClose(row.id)"
            >关闭</el-button>
            <el-popconfirm teleported :persistent="false" popper-class="delete-popconfirm" title="确定删除此试卷吗？" @confirm="handleDelete(row.id)">
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
import { ElMessage } from 'element-plus'
import { getExamList, deleteExam, publishExam, closeExam } from '@/api/exams'
import type { Exam } from '@/types'

const loading = ref(false)
const examList = ref<Exam[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const searchForm = reactive({
  keyword: '',
  status: undefined as string | undefined,
})

onMounted(() => getList())

async function getList() {
  loading.value = true
  try {
    const result = await getExamList({
      page: currentPage.value,
      pageSize: pageSize.value,
      ...searchForm,
    })
    examList.value = result.list
    total.value = result.total
  } catch {
    examList.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() { currentPage.value = 1; getList() }
function resetSearch() { searchForm.keyword = ''; searchForm.status = undefined; currentPage.value = 1; getList() }

async function handlePublish(id: number) {
  try {
    await publishExam(id)
    ElMessage.success('发布成功')
    getList()
  } catch { /* handled */ }
}

async function handleClose(id: number) {
  try {
    await closeExam(id)
    ElMessage.success('已关闭')
    getList()
  } catch { /* handled */ }
}

async function handleDelete(id: number) {
  try {
    await deleteExam(id)
    ElMessage.success('删除成功')
    getList()
  } catch { /* handled */ }
}
</script>

<style scoped lang="scss">
.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
