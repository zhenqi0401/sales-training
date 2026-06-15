import http from './index'
import type { ApiResponse } from '@/types'

function unwrapResponse<T>(request: Promise<unknown>) {
  return request as Promise<ApiResponse<T>>
}

export const salesApi = {
  getSalesList() {
    return unwrapResponse<Array<{
      id: number
      username: string
      real_name: string
      avatar: string
      phone: string
      sales_count: number
      deal_count: number
      methodology_count: number
      methodologies: Array<{
        id: number
        title: string
        content: string
        source: string
        created_at: string
      }>
    }>>(http.get('/sales/admin/sales-list'))
  },

  getDashboard() {
    return unwrapResponse<{
      totalSales: number
      totalAudioFiles: number
      totalMethodologies: number
    }>(http.get<ApiResponse<{ totalSales: number; totalAudioFiles: number; totalMethodologies: number }>>('/sales/dashboard'))
  },

  getMethodologies(page = 1, pageSize = 20) {
    return unwrapResponse<{
      total: number
      page: number
      pageSize: number
      items: Array<{
        id: number
        title: string
        content: string
        source: string
        tags: string
        status: string
        created_at: string
      }>
    }>(http.get('/sales/methodologies', { params: { page, page_size: pageSize } }))
  },

  getMethodology(id: number) {
    return unwrapResponse<{
      id: number
      title: string
      content: string
      source: string
      tags: string
      status: string
      created_at: string
    }>(http.get(`/sales/methodologies/${id}`))
  },

  uploadAudioFile(file: File) {
    const form = new FormData()
    form.append('file', file)
    return unwrapResponse<{
      id: number
      file_url: string
      filename: string
      file_size: number
      status: string
    }>(http.post('/sales/audio-files', form))
  },

  createMethodology(title: string, content: string) {
    return unwrapResponse<{
      id: number
      title: string
      content: string
      source: string
      created_at: string
    }>(http.post('/sales/methodologies', { title, content, source: 'ai' }))
  },

  getMyAudioFiles(page = 1, pageSize = 20) {
    return unwrapResponse<{
      total: number
      items: Array<{
        id: number
        file_url: string
        filename: string
        duration: number
        file_size: number
        status: string
        created_at: string
      }>
    }>(http.get('/sales/audio-files/my', { params: { page, page_size: pageSize } }))
  },
}
