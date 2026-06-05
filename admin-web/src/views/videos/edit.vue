<template>
  <div class="page-container">
    <div class="page-header">
      <h2>{{ isEditing ? '编辑视频' : '上传视频' }}</h2>
      <p>{{ isEditing ? '修改视频信息' : '上传新的培训视频' }}</p>
    </div>

    <el-row :gutter="24">
      <el-col :xs="24" :lg="16">
        <el-card shadow="hover">
          <template #header>
            <span>基本信息</span>
          </template>

          <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
            <el-form-item label="视频标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入视频标题" maxlength="100" show-word-limit />
            </el-form-item>

            <el-form-item label="所属分类" prop="categoryId">
              <el-tree-select
                v-model="form.categoryId"
                :data="categories"
                :props="{ label: 'name', value: 'id', children: 'children' }"
                placeholder="请选择分类"
                check-strictly
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="视频描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="4"
                placeholder="请输入视频描述"
                maxlength="500"
                show-word-limit
              />
            </el-form-item>

            <el-form-item label="设为必修">
              <el-switch v-model="form.required" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="hover">
          <template #header>
            <span>视频上传</span>
          </template>

          <VideoUploader @upload-success="handleUploadSuccess" />
        </el-card>

        <el-card shadow="hover" style="margin-top: 16px">
          <template #header>
            <span>视频预览</span>
          </template>
          <div v-if="form.url" class="video-preview">
            <video :src="form.url" controls style="width: 100%; border-radius: 6px"></video>
          </div>
          <div v-else class="preview-placeholder">
            <el-icon :size="48"><VideoCamera /></el-icon>
            <p>暂无视频</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="form-actions">
      <el-button type="primary" size="large" :loading="submitting" @click="handleSave">
        {{ submitting ? '保存中...' : '保存' }}
      </el-button>
      <el-button size="large" @click="() => $router.push('/videos')">取消</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getVideoDetail, createVideo, updateVideo } from '@/api/videos'
import { getCategoryTree } from '@/api/categories'
import type { Category } from '@/types'
import VideoUploader from '@/components/common/VideoUploader.vue'

const route = useRoute()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const categories = ref<Category[]>([])

const isEditing = computed(() => !!route.params.id)

const form = reactive({
  title: '',
  description: '',
  categoryId: null as number | null,
  url: '',
  coverUrl: '',
  required: false,
})

const rules: FormRules = {
  title: [
    { required: true, message: '请输入视频标题', trigger: 'blur' },
  ],
  categoryId: [
    { required: true, message: '请选择分类', trigger: 'change' },
  ],
}

onMounted(async () => {
  await loadCategories()
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

async function loadVideo() {
  try {
    const id = Number(route.params.id)
    const video = await getVideoDetail(id)
    form.title = video.title
    form.description = video.description || ''
    form.categoryId = video.categoryId
    form.url = video.url
    form.coverUrl = video.coverUrl || ''
    form.required = video.required
  } catch {
    ElMessage.error('加载视频信息失败')
  }
}

function handleUploadSuccess(result: { url: string; coverUrl?: string }) {
  form.url = result.url
  if (result.coverUrl) {
    form.coverUrl = result.coverUrl
  }
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  if (!form.url) {
    ElMessage.warning('请先上传视频文件')
    return
  }

  submitting.value = true
  try {
    const params = {
      title: form.title,
      description: form.description,
      categoryId: form.categoryId!,
      url: form.url,
      coverUrl: form.coverUrl,
      required: form.required,
    }

    if (isEditing.value) {
      await updateVideo(Number(route.params.id), params)
      ElMessage.success('更新成功')
    } else {
      await createVideo(params)
      ElMessage.success('上传成功')
    }
  } catch {
    // Error handled by interceptor
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
.video-preview {
  video {
    max-height: 300px;
    background: #000;
  }
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: #c0c4cc;
  background: #f5f7fa;
  border-radius: 6px;

  p {
    margin: 12px 0 0;
    font-size: 14px;
  }
}

.form-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
