import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { showToast } from 'vant'
import router from '@/router'

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

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
  (error) => {
    if (error.response) {
      const { status } = error.response
      switch (status) {
        case 401:
          localStorage.removeItem('auth-token')
          localStorage.removeItem('auth-refresh-token')
          router.push('/login')
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
