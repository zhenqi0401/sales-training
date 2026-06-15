<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { salesApi } from '@/api/sales'
import http from '@/api/index'

interface Methodology {
  id: number
  title: string
  content: string
  source: string
  tags: string
  status: string
  created_at: string
}

interface AudioFile {
  id: number
  file_url: string
  filename: string
  duration: number
  file_size: number
  status: string
  created_at: string
}

const loading = ref(true)
const methodologies = ref<Methodology[]>([])
const total = ref(0)
const page = ref(1)

// Upload state
const uploading = ref(false)
const generating = ref(false)
const saving = ref(false)
const uploadedAudio = ref<AudioFile | null>(null)
const draftTitle = ref('')
const draftContent = ref('')
const showDraft = ref(false)

async function loadMethodologies() {
  loading.value = true
  try {
    const res = await salesApi.getMethodologies(page.value)
    const data = res.data
    methodologies.value = data.items || []
    total.value = data.total || 0
  } catch {
    showToast('方法论加载失败')
  } finally {
    loading.value = false
  }
}

async function handleUpload(file: File) {
  uploading.value = true
  try {
    const res = await salesApi.uploadAudioFile(file)
    uploadedAudio.value = {
      id: res.data.id,
      file_url: res.data.file_url,
      filename: res.data.filename,
      duration: 0,
      file_size: res.data.file_size,
      status: res.data.status,
      created_at: '',
    }
    showToast('上传成功')
  } catch {
    showToast('上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleGenerate() {
  if (!uploadedAudio.value) return
  generating.value = true
  showLoadingToast({ message: 'AI 分析中...', forbidClick: true, duration: 0 })
  try {
    const res = await http.post<any>('/sales/methodologies/generate', {
      audio_file_id: uploadedAudio.value.id,
    })
    const data = res.data
    draftTitle.value = data.title || ''
    draftContent.value = data.content || ''
    showDraft.value = true
    closeToast()
  } catch (e: any) {
    closeToast()
    showToast(e?.response?.data?.detail || 'AI 生成失败')
  } finally {
    generating.value = false
  }
}

async function handleSave() {
  if (!draftTitle.value || !draftContent.value) return
  saving.value = true
  try {
    await salesApi.createMethodology(draftTitle.value, draftContent.value)
    showToast('保存成功')
    showDraft.value = false
    uploadedAudio.value = null
    draftTitle.value = ''
    draftContent.value = ''
    loadMethodologies()
  } catch {
    showToast('保存失败')
  } finally {
    saving.value = false
  }
}

function handleDiscard() {
  showDraft.value = false
  draftTitle.value = ''
  draftContent.value = ''
}

const fileInput = ref<HTMLInputElement | null>(null)

function triggerUpload() {
  fileInput.value?.click()
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) handleUpload(file)
  input.value = ''
}

onMounted(loadMethodologies)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">销售方法论</h2>
      <p class="page-subtitle">上传录音 → AI 分析 → 沉淀方法论</p>
    </div>

    <!-- Upload Section -->
    <div class="upload-section">
      <div class="upload-area">
        <div class="upload-icon-wrap">
          <van-icon name="music-o" size="28" color="var(--primary)" />
        </div>
        <div class="upload-text">上传销售录音</div>
        <div class="upload-hint">支持 mp3 / wav / m4a 格式</div>
        <input
          ref="fileInput"
          type="file"
          accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg"
          style="display:none"
          :disabled="uploading"
          @change="onFileChange"
        />
        <van-button
          type="primary"
          size="small"
          round
          :loading="uploading"
          @click="triggerUpload"
        >
          选择文件
        </van-button>
      </div>

      <div v-if="uploadedAudio" class="uploaded-file">
        <van-icon name="success" color="#07c160" />
        <span class="file-name">{{ uploadedAudio.filename }}</span>
        <van-button
          type="primary"
          size="small"
          round
          :loading="generating"
          :disabled="showDraft"
          @click="handleGenerate"
        >
          AI 分析
        </van-button>
      </div>
    </div>

    <!-- Draft Result -->
    <div v-if="showDraft" class="draft-section">
      <div class="draft-header">
        <van-icon name="smile-comment-o" size="20" color="var(--primary)" />
        <span>AI 生成草稿</span>
      </div>
      <div class="draft-card">
        <div class="draft-title">{{ draftTitle }}</div>
        <div class="draft-content">{{ draftContent }}</div>
        <div class="draft-actions">
          <van-button size="small" plain @click="handleDiscard">放弃</van-button>
          <van-button
            size="small"
            type="primary"
            :loading="saving"
            @click="handleSave"
          >
            保存方法论
          </van-button>
        </div>
      </div>
    </div>

    <!-- Saved Methodologies -->
    <div class="section-divider">
      <span>已保存的方法论</span>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading">加载中...</van-loading>

    <template v-else>
      <div v-if="methodologies.length" class="method-list">
        <div
          v-for="item in methodologies"
          :key="item.id"
          class="method-card"
        >
          <div class="method-title">{{ item.title }}</div>
          <div class="method-preview">{{ item.content.slice(0, 80) }}{{ item.content.length > 80 ? '...' : '' }}</div>
          <div class="method-meta">
            <van-tag round plain type="primary">{{ item.source || '手动' }}</van-tag>
            <span class="method-date">{{ item.created_at?.slice(0, 10) }}</span>
          </div>
        </div>
      </div>
      <van-empty v-else description="暂无方法论" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page-header {
  padding: 16px 16px 8px;
  background: $card;
  margin-bottom: 4px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}
.page-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}

.upload-section {
  padding: 16px;
}
.upload-area {
  background: $card;
  border-radius: $radius;
  padding: 20px;
  text-align: center;
  box-shadow: var(--shadow-sm);
  border: 1px dashed #dcdfe6;
}
.upload-icon-wrap {
  margin-bottom: 8px;
}
.upload-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}
.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 12px;
}
.upload-btn {
  display: inline-block;
}

.uploaded-file {
  background: $card;
  border-radius: $radius;
  padding: 12px 16px;
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: var(--shadow-sm);
}
.file-name {
  flex: 1;
  font-size: 13px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.draft-section {
  margin: 0 16px 16px;
}
.draft-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: var(--primary);
  margin-bottom: 8px;
}
.draft-card {
  background: $card;
  border-radius: $radius;
  padding: 14px;
  box-shadow: var(--shadow-sm);
  border-left: 3px solid var(--primary);
}
.draft-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 6px;
}
.draft-content {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.7;
  white-space: pre-wrap;
  margin-bottom: 12px;
  max-height: 200px;
  overflow-y: auto;
}
.draft-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.section-divider {
  padding: 8px 16px;
  font-size: 13px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 8px;

  &::before, &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #ebedf0;
  }
}

.page-loading {
  padding: 36px 0;
  display: block;
  text-align: center;
}

.method-list {
  padding: 0 16px 16px;
}
.method-card {
  background: $card;
  border-radius: $radius;
  padding: 14px;
  margin-bottom: 10px;
  box-shadow: var(--shadow-sm);
}
.method-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 6px;
}
.method-preview {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 8px;
}
.method-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.method-date {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
