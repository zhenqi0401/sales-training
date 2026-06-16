<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ isEditing ? '编辑视频' : '上传视频' }}</h2>
      <p>{{ isEditing ? '修改视频信息、封面或替换视频文件' : '创建新的培训视频内容' }}</p>
    </div>

    <el-row :gutter="24">
      <el-col :xs="24" :lg="16">
        <el-card shadow="hover">
          <template #header>
            <span>视频信息</span>
          </template>

          <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
            <el-form-item label="视频标题" prop="title">
              <el-input v-model="form.title" maxlength="100" show-word-limit placeholder="请输入视频标题" />
            </el-form-item>

            <el-form-item label="所属分类" prop="categoryId">
              <el-tree-select
                v-model="form.categoryId"
                :data="categories"
                :props="treeSelectProps"
                check-strictly
                placeholder="请选择分类"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="关联产品">
              <el-select
                v-model="form.productIds"
                multiple
                filterable
                clearable
                placeholder="请选择关联产品"
                style="width: 100%"
              >
                <el-option
                  v-for="product in products"
                  :key="product.id"
                  :label="product.title"
                  :value="product.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="标签">
              <el-select
                v-model="form.tags"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入标签后回车"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="视频描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="4"
                maxlength="500"
                show-word-limit
                placeholder="请输入视频描述"
              />
            </el-form-item>

            <el-row :gutter="16">
              <el-col :xs="24" :sm="12">
                <el-form-item v-if="isEditing" label="上下架状态">
                  <el-radio-group v-model="form.status">
                    <el-radio-button label="draft">草稿</el-radio-button>
                    <el-radio-button label="published">上架</el-radio-button>
                    <el-radio-button label="archived">下架</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-form-item v-else label="上下架状态">
                  <el-tag type="info">草稿</el-tag>
                  <span class="status-hint">上传后默认为草稿，需在视频管理中手动上架</span>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="16">
              <el-col :xs="24" :sm="12">
                <el-form-item label="是否必修">
                  <el-switch v-model="form.required" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="学习时长">
                  <el-input :model-value="formatStudyDuration(form.duration)" disabled />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="16">
              <el-col :xs="24" :sm="8">
                <el-form-item label="视频时长">
                  <el-input :model-value="formatDuration(form.duration)" disabled />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="8">
                <el-form-item label="分辨率">
                  <el-input :model-value="form.resolution || '--'" disabled />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="8">
                <el-form-item label="文件大小">
                  <el-input :model-value="formatFileSize(form.fileSize)" disabled />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="hover">
          <template #header>
            <span>{{ isEditing ? '替换视频文件' : '视频上传' }}</span>
          </template>
          <VideoUploader @cover-preview="handleCoverPreview" @upload-success="handleUploadSuccess" />
        </el-card>

        <el-card shadow="hover" class="side-card">
          <template #header>
            <span>封面图</span>
          </template>
          <div class="cover-preview">
            <el-image v-if="displayCoverUrl" :src="displayCoverUrl" fit="cover" />
            <div v-else class="preview-placeholder">
              <el-icon :size="40"><Picture /></el-icon>
              <p>暂无封面</p>
            </div>
          </div>
          <div class="cover-note">{{ coverUploading ? '正在保存首帧封面...' : '上传视频后自动截取首帧作为封面' }}</div>
        </el-card>

        <el-card shadow="hover" class="side-card">
          <template #header>
            <span>视频预览</span>
          </template>
          <div v-if="form.url" class="video-preview">
            <video :src="mediaUrl(form.url)" :poster="form.coverUrl ? mediaUrl(form.coverUrl) : undefined" controls preload="metadata"></video>
          </div>
          <div v-else class="preview-placeholder">
            <el-icon :size="44"><VideoCamera /></el-icon>
            <p>暂无视频</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="form-actions">
      <el-button type="primary" size="large" :loading="submitting" @click="handleSave">保存</el-button>
      <el-button size="large" @click="router.push('/videos')">取消</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { createVideo, getVideoDetail, updateVideo, uploadGeneratedCover, type VideoUploadResult } from '@/api/videos'
import { getCategoryTree } from '@/api/categories'
import { getProductList } from '@/api/products'
import type { Category, ProductKnowledge, Video } from '@/types'
import VideoUploader from '@/components/common/VideoUploader.vue'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const categories = ref<Category[]>([])
const products = ref<ProductKnowledge[]>([])
const coverPreviewUrl = ref('')
const coverUploading = ref(false)

const isEditing = computed(() => !!route.params.id)
const displayCoverUrl = computed(() => coverPreviewUrl.value || mediaUrl(form.coverUrl))
const treeSelectProps = { label: 'name', value: 'id', children: 'children' } as any

const form = reactive({
  title: '',
  description: '',
  categoryId: null as number | null,
  productIds: [] as number[],
  tags: [] as string[],
  url: '',
  coverUrl: '',
  duration: 0,
  resolution: '',
  fileSize: 0,
  status: 'draft' as Video['status'],
  required: false,
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入视频标题', trigger: 'blur' }],
  categoryId: [{ required: true, message: '请选择所属分类', trigger: 'change' }],
}

onMounted(async () => {
  await Promise.all([loadCategories(), loadProducts()])
  if (isEditing.value) {
    await loadVideo()
  }
})

async function loadCategories() {
  try {
    categories.value = await getCategoryTree()
  } catch {
    categories.value = []
  }
}

async function loadProducts() {
  try {
    const result = await getProductList({ page: 1, pageSize: 200, status: 'published' })
    products.value = result.list
  } catch {
    products.value = []
  }
}

async function loadVideo() {
  try {
    const video = await getVideoDetail(Number(route.params.id))
    form.title = video.title
    form.description = video.description || ''
    form.categoryId = video.categoryId
    form.productIds = [...video.productIds]
    form.tags = [...video.tags]
    form.url = video.url
    form.coverUrl = video.coverUrl || ''
    coverPreviewUrl.value = ''
    form.duration = video.duration || 0
    form.resolution = video.resolution || ''
    form.fileSize = video.fileSize || 0
    form.status = video.status
    form.required = video.required
  } catch {
    ElMessage.error('加载视频信息失败')
  }
}

async function handleCoverPreview(result: { previewUrl: string; file: Blob }) {
  coverPreviewUrl.value = result.previewUrl
  coverUploading.value = true
  try {
    const uploaded = await uploadGeneratedCover(result.file)
    form.coverUrl = uploaded.coverUrl
    coverPreviewUrl.value = ''
  } catch (e: any) {
    ElMessage.warning(e?.response?.data?.detail || '首帧封面保存失败，将继续使用视频预览')
  } finally {
    coverUploading.value = false
  }
}

function handleUploadSuccess(result: VideoUploadResult) {
  form.url = result.fileUrl
  form.fileSize = result.fileSize
  form.duration = result.duration
  form.resolution = result.resolution
  if (result.coverUrl) {
    form.coverUrl = result.coverUrl
    coverPreviewUrl.value = ''
  }
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  if (!form.url) {
    ElMessage.warning('请先上传视频文件')
    return
  }
  if (!form.categoryId) {
    ElMessage.warning('请选择所属分类')
    return
  }
  if (coverUploading.value) {
    ElMessage.warning('首帧封面仍在保存，请稍后再试')
    return
  }

  submitting.value = true
  try {
    const params = {
      title: form.title,
      description: form.description,
      categoryId: form.categoryId,
      url: form.url,
      coverUrl: form.coverUrl,
      tags: form.tags,
      productIds: form.productIds,
      duration: form.duration,
      resolution: form.resolution,
      fileSize: form.fileSize,
      status: form.status,
      required: form.required,
      estDuration: studyMinutes(form.duration),
    }

    if (isEditing.value) {
      await updateVideo(Number(route.params.id), params)
      ElMessage.success('更新成功')
    } else {
      await createVideo(params)
      ElMessage.success('创建成功')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败，请检查视频信息')
    return
  } finally {
    submitting.value = false
  }
  await router.push('/videos')
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function formatDuration(seconds: number): string {
  if (!seconds) return '--'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}小时 ${m}分 ${s}秒`
  if (m > 0) return `${m}分 ${s}秒`
  return `${s}秒`
}

function studyMinutes(seconds: number): number {
  return seconds > 0 ? Math.ceil(seconds / 60) : 0
}

function formatStudyDuration(seconds: number): string {
  const minutes = studyMinutes(seconds)
  return minutes ? `${minutes} 分钟` : '--'
}

function mediaUrl(url: string): string {
  if (!url) return ''
  if (/^https?:\/\//i.test(url)) return url
  return url.startsWith('/') ? url : `/${url}`
}
</script>

<style scoped lang="scss">
.side-card {
  margin-top: 16px;
}

.cover-preview {
  width: 100%;
  aspect-ratio: 16 / 9;
  margin-bottom: 12px;
  overflow: hidden;
  border-radius: 6px;
  background: #f5f7fa;

  :deep(.el-image) {
    width: 100%;
    height: 100%;
  }
}

.cover-note {
  color: #909399;
  font-size: 13px;
  line-height: 20px;
}

.video-preview {
  video {
    width: 100%;
    max-height: 280px;
    border-radius: 6px;
    background: #000;
  }
}

.preview-placeholder {
  display: flex;
  min-height: 160px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  background: #f5f7fa;
  border-radius: 6px;

  p {
    margin: 10px 0 0;
    font-size: 14px;
  }
}

.status-hint {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}
</style>
