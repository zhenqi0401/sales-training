<template>
  <div class="video-uploader">
    <el-upload
      ref="uploadRef"
      :auto-upload="false"
      :show-file-list="false"
      :accept="'video/*'"
      :on-change="handleFileChange"
      drag
      class="upload-area"
    >
      <el-icon class="upload-icon" :size="48"><VideoCamera /></el-icon>
      <div class="upload-text">
        将视频文件拖拽到此处，或<em>点击选择文件</em>
      </div>
      <template #tip>
        <div class="upload-tip">
          支持 MP4, AVI, MOV, MKV 等格式，最大 2GB
        </div>
      </template>
    </el-upload>

    <div v-if="selectedFile" class="file-info">
      <div class="info-row">
        <span class="label">文件名：</span>
        <span>{{ selectedFile.name }}</span>
      </div>
      <div class="info-row">
        <span class="label">文件大小：</span>
        <span>{{ formatFileSize(selectedFile.size) }}</span>
      </div>
      <div v-if="videoDuration" class="info-row">
        <span class="label">视频时长：</span>
        <span>{{ formatDuration(videoDuration) }}</span>
      </div>
    </div>

    <!-- Progress -->
    <div v-if="uploading" class="upload-progress">
      <el-progress :percentage="uploadPercent" :status="uploadStatus" />
      <p class="progress-text">
        {{ uploadStatus === 'success' ? '上传完成，正在合并文件...' : `正在上传 ${uploadedChunks}/${totalChunks} 分片` }}
      </p>
    </div>

    <div class="upload-actions" v-if="selectedFile">
      <el-button type="primary" :loading="uploading" :disabled="uploading" @click="handleUpload">
        {{ uploading ? '上传中...' : '开始上传' }}
      </el-button>
      <el-button @click="resetUpload" :disabled="uploading">重新选择</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadProps } from 'element-plus'
import { post } from '@/api/index'

const CHUNK_SIZE = 5 * 1024 * 1024 // 5 MB per chunk

const emit = defineEmits<{
  (e: 'upload-success', result: { url: string; fileSize: number; duration: number }): void
}>()

const uploadRef = ref()
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const videoDuration = ref(0)
const uploadPercent = ref(0)
const uploadedChunks = ref(0)
const totalChunks = ref(0)
const uploadStatus = ref<'uploading' | 'success' | 'exception'>('uploading')

function handleFileChange(file: UploadProps['file']) {
  selectedFile.value = file.raw || null
  if (selectedFile.value) {
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      videoDuration.value = video.duration
      URL.revokeObjectURL(video.src)
    }
    video.src = URL.createObjectURL(selectedFile.value)
  }
}

async function handleUpload() {
  if (!selectedFile.value) return

  const file = selectedFile.value
  const chunkCount = Math.ceil(file.size / CHUNK_SIZE)
  totalChunks.value = chunkCount
  uploadedChunks.value = 0
  uploadPercent.value = 0
  uploadStatus.value = 'uploading'
  uploading.value = true

  try {
    // Step 1 — init upload session
    const initForm = new FormData()
    initForm.append('filename', file.name)
    initForm.append('file_size', String(file.size))
    const initRes = await post<{ upload_id: string }>('/videos/upload/init', initForm)
    const uploadId = initRes.upload_id

    // Step 2 — upload chunks
    for (let i = 0; i < chunkCount; i++) {
      const start = i * CHUNK_SIZE
      const chunk = file.slice(start, start + CHUNK_SIZE)

      const chunkForm = new FormData()
      chunkForm.append('upload_id', uploadId)
      chunkForm.append('chunk_index', String(i))
      chunkForm.append('total_chunks', String(chunkCount))
      chunkForm.append('file', chunk)

      await post('/videos/upload/chunk', chunkForm)

      uploadedChunks.value = i + 1
      uploadPercent.value = Math.round(((i + 1) / chunkCount) * 90) // 90% for upload, 10% for merge
    }

    // Step 3 — merge chunks (the last 10%)
    uploadPercent.value = 95
    const mergeForm = new FormData()
    mergeForm.append('upload_id', uploadId)
    const mergeRes = await post<{ file_url: string; file_size: number }>('/videos/upload/merge', mergeForm)

    uploadPercent.value = 100
    uploadStatus.value = 'success'

    emit('upload-success', {
      url: mergeRes.file_url,
      fileSize: mergeRes.file_size,
      duration: videoDuration.value,
    })

    ElMessage.success('上传成功')
    resetUpload()
  } catch (e: any) {
    uploadStatus.value = 'exception'
    const msg = e?.response?.data?.detail || '上传失败，请重试'
    ElMessage.error(msg)
  } finally {
    uploading.value = false
  }
}

function resetUpload() {
  selectedFile.value = null
  videoDuration.value = 0
  uploadPercent.value = 0
  uploadedChunks.value = 0
  totalChunks.value = 0
  if (uploadRef.value) uploadRef.value.clearFiles()
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}时${m}分${s}秒`
  if (m > 0) return `${m}分${s}秒`
  return `${s}秒`
}
</script>

<style scoped lang="scss">
.video-uploader {
  .upload-area {
    width: 100%;
    .upload-icon { margin-bottom: 16px; }
    .upload-text {
      font-size: 14px; color: #606266;
      em { color: var(--primary-color); font-style: normal; }
    }
    .upload-tip { font-size: 12px; color: #909399; margin-top: 8px; }
  }

  .file-info {
    margin-top: 16px; padding: 16px; background: #f5f7fa; border-radius: 6px;
    .info-row { font-size: 14px; color: #606266; margin-bottom: 8px;
      &:last-child { margin-bottom: 0; }
      .label { color: #909399; }
    }
  }

  .upload-progress {
    margin-top: 16px;
    .progress-text { font-size: 12px; color: #909399; margin: 8px 0 0; text-align: center; }
  }

  .upload-actions { margin-top: 16px; display: flex; gap: 12px; }
}
</style>
