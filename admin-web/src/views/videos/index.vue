<template>
  <div class="page-container">
    <div class="page-header">
      <h2>视频管理</h2>
      <p>管理培训课程视频内容</p>
    </div>

    <!-- Search Form -->
    <div class="search-form">
      <el-input
        v-model="searchForm.keyword"
        placeholder="搜索视频名称"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="searchForm.categoryId"
        placeholder="选择分类"
        clearable
        style="width: 160px"
        @change="handleSearch"
      >
        <el-option
          v-for="cat in categories"
          :key="cat.id"
          :label="cat.name"
          :value="cat.id"
        />
      </el-select>
      <el-select
        v-model="searchForm.status"
        placeholder="选择状态"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option label="已发布" value="published" />
        <el-option label="草稿" value="draft" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <!-- Table -->
    <div class="table-container">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="$router.push('/videos/edit')">
            <el-icon><Plus /></el-icon>上传视频
          </el-button>
        </div>
        <div class="toolbar-right">
          <span class="table-total">共 {{ total }} 个视频</span>
        </div>
      </div>

      <el-table :data="videoList" stripe v-loading="loading" empty-text="暂无视频数据">
        <el-table-column label="封面" width="120">
          <template #default="{ row }">
            <div class="video-cover">
              <el-image
                :src="row.coverUrl || ''"
                fit="cover"
                style="width: 80px; height: 45px; border-radius: 4px"
              >
                <template #error>
                  <div class="cover-placeholder">
                    <el-icon :size="24"><VideoCamera /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="视频名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="categoryName" label="分类" width="120" />
        <el-table-column prop="duration" label="时长" width="100" align="center">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column prop="viewCount" label="观看" width="80" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'published'" type="success" size="small">已发布</el-tag>
            <el-tag v-else-if="row.status === 'draft'" type="info" size="small">草稿</el-tag>
            <el-tag v-else type="warning" size="small">已归档</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="必修" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.required" type="danger" size="small">必修</el-tag>
            <span v-else class="optional-text">选修</span>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="$router.push(`/videos/edit/${row.id}`)">编辑</el-button>
            <el-button
              text
              :type="row.status === 'published' ? 'warning' : 'success'"
              size="small"
              @click="toggleStatus(row)"
            >
              {{ row.status === 'published' ? '下架' : '发布' }}
            </el-button>
            <el-popconfirm title="确定删除此视频吗？" @confirm="handleDelete(row.id)">
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
import { getVideoList, deleteVideo, toggleVideoStatus } from '@/api/videos'
import { getCategoryList } from '@/api/categories'
import type { Video, Category } from '@/types'

const loading = ref(false)
const videoList = ref<Video[]>([])
const categories = ref<Category[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const searchForm = reactive({
  keyword: '',
  categoryId: undefined as number | undefined,
  status: undefined as string | undefined,
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
    const result = await getVideoList({
      page: currentPage.value,
      pageSize: pageSize.value,
      ...searchForm,
    })
    videoList.value = result.list
    total.value = result.total
  } catch {
    videoList.value = []
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
  searchForm.status = undefined
  currentPage.value = 1
  getList()
}

async function toggleStatus(row: Video) {
  const newStatus = row.status === 'published' ? 'archived' : 'published'
  try {
    await toggleVideoStatus(row.id, newStatus)
    ElMessage.success(row.status === 'published' ? '已下架' : '已发布')
    getList()
  } catch {
    // Error handled by interceptor
  }
}

async function handleDelete(id: number) {
  try {
    await deleteVideo(id)
    ElMessage.success('删除成功')
    getList()
  } catch {
    // Error handled by interceptor
  }
}

function formatDuration(seconds: number): string {
  if (!seconds) return '--'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  if (m > 60) {
    const h = Math.floor(m / 60)
    return `${h}时${m % 60}分`
  }
  return `${m}分${s}秒`
}
</script>

<style scoped lang="scss">
.video-cover {
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-placeholder {
  width: 80px;
  height: 45px;
  background: #f5f7fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
}

.optional-text {
  font-size: 12px;
  color: #909399;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
