import axios from 'axios'
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const request: AxiosInstance = axios.create({
  baseURL,
  timeout: 10 * 60 * 1000,
})

function normalizeParams(params?: Record<string, any>): Record<string, any> | undefined {
  if (!params) return params

  const normalized: Record<string, any> = {}
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return

    const normalizedKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)
    normalized[normalizedKey] = value
  })
  return normalized
}

function normalizeResponseData<T>(data: T): T {
  if (data && typeof data === 'object' && 'items' in data) {
    const pageData = data as Record<string, any>
    return {
      ...pageData,
      list: pageData.items,
      pageSize: pageData.page_size,
      totalPages: pageData.total_pages,
    } as T
  }
  return data
}

// Attach JWT from localStorage
request.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const raw = localStorage.getItem('auth-store')
  if (raw) {
    try {
      const { token } = JSON.parse(raw)
      if (token) config.headers.Authorization = `Bearer ${token}`
    } catch { /* ignore */ }
  }
  return config
})

// Handle errors
request.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    const status = error.response?.status
    if (status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      localStorage.removeItem('auth-store')
      router.push('/login')
    } else if (status === 403) {
      ElMessage.error('无权限')
    } else if (status === 500) {
      ElMessage.error('服务器错误')
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时')
    } else if (!status) {
      ElMessage.error('网络错误')
    }
    return Promise.reject(error)
  },
)

export function get<T>(url: string, params?: Record<string, any>): Promise<T> {
  return request.get(url, { params: normalizeParams(params) }).then((r) => normalizeResponseData<T>(r.data))
}
export function post<T>(url: string, data?: Record<string, any>): Promise<T> {
  return request.post(url, data).then((r) => r.data)
}
export function put<T>(url: string, data?: Record<string, any>): Promise<T> {
  return request.put(url, data).then((r) => r.data)
}
export function del<T>(url: string, params?: Record<string, any>): Promise<T> {
  return request.delete(url, { params }).then((r) => r.data)
}

export default request
