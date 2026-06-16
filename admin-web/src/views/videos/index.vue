<template>
  <div class="page-container">
    <div class="page-header">
      <h2>视频管理</h2>
      <p>管理培训视频的上传、上架、分类和关联产品</p>
    </div>

    <div class="search-form">
      <el-input
        v-model="searchForm.keyword"
        clearable
        placeholder="搜索标题或描述"
        style="width: 220px"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="searchForm.categoryId"
        clearable
        placeholder="选择分类"
        style="width: 170px"
        @change="handleSearch"
      >
        <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
      </el-select>
      <el-select
        v-model="searchForm.status"
        clearable
        placeholder="上下架状态"
        style="width: 150px"
        @change="handleSearch"
      >
        <el-option label="草稿" value="draft" />
        <el-option label="转码中" value="transcoding" />
        <el-option label="生成中" value="generating" />
        <el-option label="已上架" value="published" />
        <el-option label="已下架" value="archived" />
      </el-select>
      <el-select
        v-model="searchForm.isRequired"
        clearable
        placeholder="是否必修"
        style="width: 130px"
        @change="handleSearch"
      >
        <el-option label="必修" :value="true" />
        <el-option label="选修" :value="false" />
      </el-select>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="resetSearch">重置</el-button>
    </div>

    <div class="table-container">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="router.push('/videos/edit')">
            <el-icon><Plus /></el-icon>
            上传视频
          </el-button>
          <el-button :disabled="!selectedIds.length" @click="handleBatchStatus('published')">批量上架</el-button>
          <el-button :disabled="!selectedIds.length" @click="handleBatchStatus('archived')">批量下架</el-button>
        </div>
        <div class="toolbar-right">
          <span class="table-total">共 {{ total }} 个视频</span>
        </div>
      </div>

      <el-table
        :data="videoList"
        stripe
        v-loading="loading"
        empty-text="暂无视频数据"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column label="封面" width="116">
          <template #default="{ row }">
            <div class="video-cover">
              <el-image :src="mediaUrl(row.coverUrl || '')" fit="cover">
                <template #error>
                  <div class="cover-placeholder">
                    <el-icon :size="22"><VideoCamera /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="视频信息" min-width="260">
          <template #default="{ row }">
            <div class="video-title">{{ row.title }}</div>
            <div class="video-meta">
              {{ row.categoryName || '未分类' }} · {{ formatDuration(row.duration) }} · {{ row.resolution || '未知分辨率' }}
            </div>
            <div class="tag-list" v-if="row.tags.length">
              <el-tag v-for="tag in row.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="关联产品" min-width="180">
          <template #default="{ row }">
            <span v-if="!row.productNames?.length" class="muted-text">未关联</span>
            <div v-else class="product-list">
              <el-tag v-for="name in row.productNames" :key="name" size="small">{{ name }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="110" align="center">
          <template #default="{ row }">{{ formatFileSize(row.fileSize) }}</template>
        </el-table-column>
        <el-table-column label="必修" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.required" type="danger" size="small">必修</el-tag>
            <span v-else class="muted-text">选修</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.status === 'transcoding' || row.status === 'generating'"
              :content="pipelineTooltip(row)"
              placement="top"
              :disabled="!pipelineTooltip(row)"
            >
              <el-tag v-if="row.status === 'transcoding'" type="primary" size="small">转码中</el-tag>
              <el-tag v-else-if="row.status === 'generating'" type="warning" size="small">生成中</el-tag>
            </el-tooltip>
            <el-tag v-else-if="row.status === 'published'" type="success" size="small">已上架</el-tag>
            <el-tag v-else-if="row.status === 'draft'" type="info" size="small">草稿</el-tag>
            <el-tag v-else type="warning" size="small">已下架</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right" align="center">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="router.push(`/videos/edit/${row.id}`)">编辑</el-button>
            <el-button
              v-if="row.status === 'transcoding' || row.status === 'generating'"
              text
              type="warning"
              size="small"
              :loading="retryingIds.has(row.id)"
              @click="handleRetry(row as Video)"
            >
              重新处理
            </el-button>
            <el-button
              v-else
              text
              :type="row.status === 'published' ? 'warning' : 'success'"
              size="small"
              :loading="togglingIds.has(row.id)"
              @click="toggleStatus(row as Video)"
            >
              {{ row.status === 'published' ? '下架' : '上架' }}
            </el-button>
            <el-button text type="danger" size="small" @click="handleDelete((row as Video).id)">删除</el-button>
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
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { confirmDanger } from '@/utils/confirm'
import { batchUpdateVideoStatus, deleteVideo, getVideoList, retryVideoPipeline, toggleVideoStatus } from '@/api/videos'
import { getCategoryList } from '@/api/categories'
import type { Category, Video } from '@/types'

const router = useRouter()
const loading = ref(false)
const videoList = ref<Video[]>([])
const categories = ref<Category[]>([])
const selectedIds = ref<number[]>([])
const togglingIds = ref(new Set<number>())
const retryingIds = ref(new Set<number>())
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const searchForm = reactive({
  keyword: '',
  categoryId: undefined as number | undefined,
  status: undefined as string | undefined,
  isRequired: undefined as boolean | undefined,
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
  searchForm.isRequired = undefined
  currentPage.value = 1
  getList()
}

function handleSelectionChange(rows: Video[]) {
  selectedIds.value = rows.map((row) => row.id)
}

async function toggleStatus(row: Video) {
  if (row.status === 'transcoding' || row.status === 'generating') return
  const newStatus = row.status === 'published' ? 'archived' : 'published'
  togglingIds.value.add(row.id)
  try {
    await toggleVideoStatus(row.id, newStatus)
    ElMessage.success(newStatus === 'published' ? '已上架' : '已下架')
    getList()
  } catch {
    // Error handled by interceptor.
  } finally {
    togglingIds.value.delete(row.id)
  }
}

async function handleRetry(row: Video) {
  retryingIds.value.add(row.id)
  try {
    await retryVideoPipeline(row.id)
    ElMessage.success('已重新开始处理，请等待转码和 AI 出题完成')
    getList()
  } catch {
    // Error handled by interceptor.
  } finally {
    retryingIds.value.delete(row.id)
  }
}

async function handleBatchStatus(status: string) {
  if (!selectedIds.value.length) return
  try {
    await batchUpdateVideoStatus(selectedIds.value, status)
    ElMessage.success(status === 'published' ? '批量上架成功' : '批量下架成功')
    selectedIds.value = []
    getList()
  } catch {
    // Error handled by interceptor.
  }
}

async function handleDelete(id: number) {
  try {
    await confirmDanger('确定删除该视频吗？此操作不可恢复。', { title: '确认删除', confirmButtonText: '删除' })
    await deleteVideo(id)
    ElMessage.success('视频已删除')
    getList()
  } catch {
    // Error handled by interceptor.
  }
}

function formatDuration(seconds: number): string {
  if (!seconds) return '--'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}小时${m}分`
  if (m > 0) return `${m}分${s}秒`
  return `${s}秒`
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '--'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function formatDate(value: string): string {
  if (!value) return '--'
  return value.replace('T', ' ').slice(0, 16)
}

const STEP_LABELS: Record<string, string> = {
  init: '初始化',
  transcode: '视频压缩',
  asr: '语音转文字',
  ai_generate: 'AI 生成题目',
  done: '完成',
}
const STATUS_LABELS: Record<string, string> = {
  running: '进行中',
  success: '已完成',
  failed: '失败',
  skipped: '已跳过',
}

function pipelineTooltip(row: any): string {
  const log = row.pipelineLog || row.pipeline_log
  if (!log || typeof log !== 'object') return ''
  const steps = Object.entries(log as Record<string, any>)
  if (!steps.length) return ''
  return steps
    .map(([key, val]: [string, any]) => {
      const step = STEP_LABELS[key] || key
      const status = STATUS_LABELS[val.status] || val.status
      return `${step}: ${status}${val.message ? ' — ' + val.message : ''}`
    })
    .join('\n')
}

function mediaUrl(url: string): string {
  if (!url) return ''
  if (/^https?:\/\//i.test(url)) return url
  return url.startsWith('/') ? url : `/${url}`
}
</script>

<style scoped lang="scss">
.video-cover {
  width: 88px;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: 4px;
  background: #f5f7fa;

  :deep(.el-image) {
    width: 100%;
    height: 100%;
  }
}

.cover-placeholder {
  display: flex;
  width: 88px;
  height: 50px;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  background: #f5f7fa;
}

.video-title {
  font-weight: 600;
  color: #303133;
}

.video-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.tag-list,
.product-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.muted-text {
  font-size: 12px;
  color: #909399;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
