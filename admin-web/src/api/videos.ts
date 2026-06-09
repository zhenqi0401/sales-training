import { get, post, put, del } from './index'
import type { Video, VideoUploadParams, PageResult } from '@/types'

type BackendPage<T> = PageResult<T> & { items?: T[] }

export interface VideoUploadResult {
  fileUrl: string
  fileSize: number
  duration: number
  resolution: string
  coverUrl?: string
  sha256?: string
  uploadId?: string
  compressed?: boolean
  compressionPending?: boolean
}

function normalizeVideo(data: any): Video {
  return {
    ...data,
    categoryId: data.categoryId ?? data.category_id ?? null,
    categoryName: data.categoryName ?? data.category_name ?? '',
    url: data.url ?? data.file_url ?? '',
    coverUrl: data.coverUrl ?? data.cover_url ?? '',
    tags: Array.isArray(data.tags) ? data.tags : [],
    productIds: Array.isArray(data.productIds)
      ? data.productIds
      : Array.isArray(data.product_ids)
        ? data.product_ids
        : [],
    productNames: Array.isArray(data.productNames)
      ? data.productNames
      : Array.isArray(data.product_names)
        ? data.product_names
        : [],
    duration: data.duration ?? 0,
    resolution: data.resolution ?? '',
    fileSize: data.fileSize ?? data.file_size ?? 0,
    status: data.status ?? 'draft',
    viewCount: data.viewCount ?? data.view_count ?? 0,
    required: data.required ?? data.is_required ?? false,
    sortOrder: data.sortOrder ?? data.sort_order ?? 0,
    estDuration: data.estDuration ?? data.est_duration ?? 0,
    createdAt: data.createdAt ?? data.created_at ?? '',
    updatedAt: data.updatedAt ?? data.updated_at ?? '',
  }
}

function normalizeVideoPage(data: BackendPage<any>): PageResult<Video> {
  return {
    ...data,
    list: (data.list ?? data.items ?? []).map(normalizeVideo),
  }
}

function normalizeUploadResult(data: any): VideoUploadResult {
  return {
    fileUrl: data.fileUrl ?? data.file_url ?? '',
    fileSize: data.fileSize ?? data.file_size ?? 0,
    duration: data.duration ?? 0,
    resolution: data.resolution ?? '',
    coverUrl: data.coverUrl ?? data.cover_url ?? '',
    sha256: data.sha256,
    uploadId: data.uploadId ?? data.upload_id ?? '',
    compressed: !!(data.compressed),
    compressionPending: !!(data.compressionPending ?? data.compression_pending),
  }
}

function toVideoPayload(params: Partial<VideoUploadParams>): Record<string, any> {
  return {
    title: params.title,
    description: params.description,
    category_id: params.categoryId,
    file_url: params.url,
    cover_url: params.coverUrl,
    tags: params.tags,
    product_ids: params.productIds,
    duration: params.duration,
    resolution: params.resolution,
    file_size: params.fileSize,
    status: params.status,
    sort_order: params.sortOrder,
    is_required: params.required,
    est_duration: params.estDuration,
  }
}

export function getVideoList(params: {
  page: number
  pageSize: number
  categoryId?: number
  status?: string
  keyword?: string
  isRequired?: boolean
}): Promise<PageResult<Video>> {
  return get<BackendPage<any>>('/videos/', params).then(normalizeVideoPage)
}

export function getVideoDetail(id: number): Promise<Video> {
  return get<any>(`/videos/${id}`).then(normalizeVideo)
}

export function createVideo(params: VideoUploadParams): Promise<Video> {
  return post<any>('/videos/', toVideoPayload(params)).then(normalizeVideo)
}

export function updateVideo(id: number, params: Partial<VideoUploadParams>): Promise<Video> {
  return put<any>(`/videos/${id}`, toVideoPayload(params)).then(normalizeVideo)
}

export function deleteVideo(id: number): Promise<void> {
  return del<void>(`/videos/${id}`)
}

export function toggleVideoStatus(id: number, status: string): Promise<Video> {
  return put<any>(`/videos/${id}/status`, { status }).then(normalizeVideo)
}

export function batchUpdateVideoStatus(ids: number[], status: string): Promise<void> {
  return post<void>('/videos/batch/status', { ids, status })
}

export function uploadGeneratedCover(file: Blob): Promise<{ coverUrl: string }> {
  const formData = new FormData()
  formData.append('file', file, 'cover.jpg')
  return post<any>('/videos/upload/cover', formData).then((data) => ({
    coverUrl: data.coverUrl ?? data.cover_url ?? '',
  }))
}

export function initVideoUpload(file: File): Promise<{ uploadId: string }> {
  const formData = new FormData()
  formData.append('filename', file.name)
  formData.append('file_size', String(file.size))
  return post<any>('/videos/upload/init', formData).then((data) => ({
    uploadId: data.uploadId ?? data.upload_id,
  }))
}

export function uploadVideoChunk(params: {
  uploadId: string
  chunkIndex: number
  totalChunks: number
  chunk: Blob
}): Promise<void> {
  const formData = new FormData()
  formData.append('upload_id', params.uploadId)
  formData.append('chunk_index', String(params.chunkIndex))
  formData.append('total_chunks', String(params.totalChunks))
  formData.append('file', params.chunk)
  return post<void>('/videos/upload/chunk', formData)
}

export function mergeVideoUpload(uploadId: string): Promise<VideoUploadResult> {
  const formData = new FormData()
  formData.append('upload_id', uploadId)
  return post<any>('/videos/upload/merge', formData).then(normalizeUploadResult)
}
