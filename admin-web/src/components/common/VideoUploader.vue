<template>
  <div class="video-uploader">
    <el-upload
      ref="uploadRef"
      :auto-upload="false"
      :show-file-list="false"
      accept=".mp4,video/mp4"
      :on-change="handleFileChange"
      drag
      class="upload-area"
    >
      <el-icon class="upload-icon" :size="44"><VideoCamera /></el-icon>
      <div class="upload-text">拖拽视频到此处，或<em>点击选择</em></div>
      <template #tip>
        <div class="upload-tip">仅支持 MP4 格式，单个文件最大 2GB</div>
      </template>
    </el-upload>

    <div v-if="selectedFile" class="file-info">
      <div class="info-row">
        <span class="label">文件名</span>
        <span>{{ selectedFile.name }}</span>
      </div>
      <div class="info-row">
        <span class="label">文件大小</span>
        <span>{{ formatFileSize(selectedFile.size) }}</span>
      </div>
      <div class="info-row" v-if="videoDuration">
        <span class="label">时长</span>
        <span>{{ formatDuration(videoDuration) }}</span>
      </div>
      <div class="info-row" v-if="videoResolution">
        <span class="label">分辨率</span>
        <span>{{ videoResolution }}</span>
      </div>
    </div>

    <div v-if="uploading || compressing" class="upload-progress">
      <el-progress
        :percentage="uploadPercent"
        :status="uploadStatus === 'uploading' ? undefined : uploadStatus"
        :striped="compressing"
        :striped-flow="compressing"
      />
      <p class="progress-text">
        <template v-if="compressing">正在压缩为手机端 MP4，请稍候...</template>
        <template v-else>{{ uploadStatus === 'success' ? '上传完成' : `正在上传 ${uploadedChunks}/${totalChunks} 个分片` }}</template>
      </p>
    </div>

    <div class="upload-actions" v-if="selectedFile">
      <el-button type="primary" :loading="uploading || compressing" :disabled="uploading || compressing" @click="handleUpload">
        {{ uploading ? '上传中' : compressing ? '压缩中' : '开始上传' }}
      </el-button>
      <el-button :disabled="uploading || compressing" @click="resetUpload">重新选择</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import {
  initVideoUpload,
  mergeVideoUpload,
  uploadVideoChunk,
  type VideoUploadResult,
} from '@/api/videos'

const CHUNK_SIZE = 5 * 1024 * 1024
const MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
const ALLOWED_EXTENSIONS = ['mp4']

const emit = defineEmits<{
  (e: 'upload-success', result: VideoUploadResult): void
  (e: 'cover-preview', result: { previewUrl: string; file: Blob }): void
}>()

const uploadRef = ref()
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const videoDuration = ref(0)
const videoResolution = ref('')
const uploadPercent = ref(0)
const uploadedChunks = ref(0)
const totalChunks = ref(0)
const uploadStatus = ref<'uploading' | 'success' | 'exception'>('uploading')
const compressing = ref(false)

function handleFileChange(file: UploadFile) {
  const rawFile = file.raw || null
  if (!rawFile) return

  const ext = rawFile.name.split('.').pop()?.toLowerCase() || ''
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    ElMessage.warning('仅支持 MP4 格式')
    resetUpload()
    return
  }
  if (rawFile.size > MAX_FILE_SIZE) {
    ElMessage.warning('视频文件不能超过 2GB')
    resetUpload()
    return
  }

  selectedFile.value = rawFile
  readVideoMetadata(rawFile)
}

function readVideoMetadata(file: File) {
  const video = document.createElement('video')
  const objectUrl = URL.createObjectURL(file)
  video.preload = 'metadata'
  video.onloadedmetadata = () => {
    videoDuration.value = Math.round(video.duration || 0)
    videoResolution.value = video.videoWidth && video.videoHeight
      ? `${video.videoWidth}x${video.videoHeight}`
      : ''
    captureFirstFrame(video, objectUrl)
  }
  video.onerror = () => {
    URL.revokeObjectURL(objectUrl)
  }
  video.src = objectUrl
}

function captureFirstFrame(video: HTMLVideoElement, objectUrl: string) {
  video.currentTime = 0
  video.onseeked = () => {
    try {
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const context = canvas.getContext('2d')
      if (context && canvas.width && canvas.height) {
        context.drawImage(video, 0, 0, canvas.width, canvas.height)
        canvas.toBlob((blob) => {
          if (blob) {
            emit('cover-preview', {
              previewUrl: canvas.toDataURL('image/jpeg', 0.86),
              file: blob,
            })
          }
        }, 'image/jpeg', 0.86)
      }
    } finally {
      URL.revokeObjectURL(objectUrl)
    }
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
    const { uploadId } = await initVideoUpload(file)

    for (let i = 0; i < chunkCount; i += 1) {
      const start = i * CHUNK_SIZE
      const chunk = file.slice(start, start + CHUNK_SIZE)

      await uploadVideoChunk({
        uploadId,
        chunkIndex: i,
        totalChunks: chunkCount,
        chunk,
      })

      uploadedChunks.value = i + 1
      uploadPercent.value = Math.round(((i + 1) / chunkCount) * 90)
    }

    uploading.value = false
    compressing.value = true
    uploadPercent.value = 95
    ElMessage.info('视频已上传，正在快速压缩为手机端 MP4')
    const result = await mergeVideoUpload(uploadId)

    uploadPercent.value = 100
    uploadStatus.value = 'success'
    compressing.value = false

    emit('upload-success', {
      ...result,
      duration: result.duration || videoDuration.value,
      resolution: result.resolution || videoResolution.value,
    })
    if (result.compressionPending) {
      ElMessage.success('视频已上传，可先保存；后台将继续压缩并自动替换')
    } else {
      ElMessage.success('视频上传并压缩完成')
    }
    resetUpload()
  } catch (e: any) {
    uploadStatus.value = 'exception'
    compressing.value = false
    ElMessage.error(e?.response?.data?.detail || '上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

function resetUpload() {
  selectedFile.value = null
  videoDuration.value = 0
  videoResolution.value = ''
  uploadPercent.value = 0
  uploadedChunks.value = 0
  totalChunks.value = 0
  compressing.value = false
  uploadRef.value?.clearFiles()
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}小时 ${m}分 ${s}秒`
  if (m > 0) return `${m}分 ${s}秒`
  return `${s}秒`
}
</script>

<style scoped lang="scss">
.video-uploader {
  .upload-area {
    width: 100%;
  }

  .upload-icon {
    margin-bottom: 12px;
    color: #409eff;
  }

  .upload-text {
    font-size: 14px;
    color: #606266;

    em {
      color: #409eff;
      font-style: normal;
    }
  }

  .upload-tip {
    margin-top: 8px;
    font-size: 12px;
    color: #909399;
  }

  .file-info {
    margin-top: 16px;
    padding: 14px 16px;
    background: #f5f7fa;
    border-radius: 6px;
  }

  .info-row {
    display: flex;
    gap: 12px;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 14px;
    color: #303133;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .label {
    flex: 0 0 64px;
    color: #909399;
  }

  .upload-progress {
    margin-top: 16px;
  }

  .progress-text {
    margin: 8px 0 0;
    text-align: center;
    font-size: 12px;
    color: #909399;
  }

  .upload-actions {
    display: flex;
    gap: 12px;
    margin-top: 16px;
  }
}
</style>
