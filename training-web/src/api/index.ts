import axios from 'axios'
import type { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { showToast } from 'vant'
import router from '@/router'
import type { ApiResponse } from '@/types'

type RefreshPayload = {
  token: string
  refreshToken: string
}

type RetryConfig = InternalAxiosRequestConfig & {
  _retry?: boolean
}

const AUTH_TOKEN_REFRESHED_EVENT = 'auth-token-refreshed'

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 180000
})

const refreshHttp: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 180000
})

let refreshPromise: Promise<string | null> | null = null

function persistTokens(data: RefreshPayload) {
  localStorage.setItem('auth-token', data.token)
  localStorage.setItem('auth-refresh-token', data.refreshToken)
  window.dispatchEvent(new CustomEvent(AUTH_TOKEN_REFRESHED_EVENT, { detail: data }))
}

function clearAuthState() {
  localStorage.removeItem('auth-token')
  localStorage.removeItem('auth-refresh-token')
  localStorage.removeItem('auth-user')
}

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('auth-refresh-token')
  if (!refreshToken) return null

  if (!refreshPromise) {
    refreshPromise = refreshHttp
      .post<ApiResponse<RefreshPayload>>('/auth/refresh', { refreshToken })
      .then((response) => {
        const data = response.data.data
        if (!data?.token || !data?.refreshToken) return null
        persistTokens(data)
        return data.token
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

// Request interceptor — attach JWT
http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('auth-token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor — handle auth & errors
http.interceptors.response.use(
  (response: AxiosResponse) => {
    const { code, message } = response.data
    if (code === 0 || code === 200) {
      return response.data
    }
    showToast(message || '请求失败')
    return Promise.reject(new Error(message))
  },
  async (error: AxiosError) => {
    if (error.response) {
      const { status } = error.response
      switch (status) {
        case 401:
          {
            const originalRequest = error.config as RetryConfig | undefined
            if (originalRequest && !originalRequest._retry) {
              originalRequest._retry = true
              const newToken = await refreshAccessToken()
              if (newToken && originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${newToken}`
                return http(originalRequest)
              }
            }
          }
          clearAuthState()
          if (router.currentRoute.value.path !== '/login') {
            router.push('/login')
          }
          showToast('登录已过期，请重新登录')
          break
        case 403:
          showToast('没有权限访问')
          break
        case 404:
          showToast('请求的资源不存在')
          break
        case 500:
          showToast('服务器错误')
          break
        default:
          showToast(error.message || '网络错误')
      }
    } else if (error.code === 'ECONNABORTED') {
      showToast('请求超时')
    } else {
      showToast('网络异常，请检查网络连接')
    }
    return Promise.reject(error)
  }
)

export default http
