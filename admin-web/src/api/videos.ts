import { get, post, put, del } from './index'
import type { Video, VideoUploadParams, PageResult } from '@/types'

export function getVideoList(params: {
  page: number
  pageSize: number
  categoryId?: number
  status?: string
  keyword?: string
}): Promise<PageResult<Video>> {
  return get<PageResult<Video>>('/videos/', params)
}

export function getVideoDetail(id: number): Promise<Video> {
  return get<Video>(`/videos/${id}`)
}

export function createVideo(params: VideoUploadParams): Promise<Video> {
  return post<Video>('/videos/', params)
}

export function updateVideo(id: number, params: Partial<VideoUploadParams>): Promise<Video> {
  return put<Video>(`/videos/${id}`, params)
}

export function deleteVideo(id: number): Promise<void> {
  return del<void>(`/videos/${id}`)
}

export function uploadVideoFile(file: File): Promise<{ url: string; coverUrl: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return post<{ url: string; coverUrl: string }>('/videos/upload', formData)
}

export function toggleVideoStatus(id: number, status: string): Promise<Video> {
  return put<Video>(`/videos/${id}/status`, { status })
}
