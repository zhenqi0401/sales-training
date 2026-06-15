import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { post } from '@/api/index'
import type { LoginResult, UserInfo } from '@/types'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>('')
  const refreshTokenVal = ref<string>('')
  const userInfo = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'admin')

  async function login(username: string, password: string) {
    const res = await post<any>('/auth/login', { username, password })

    // Support both ApiResponse envelope and legacy bare format
    let t: string
    let user: any

    if (res.data && typeof res.data === 'object' && res.data.token && res.data.user) {
      // New ApiResponse format: { code, message, data: { token, refreshToken, user } }
      if (res.code !== undefined && res.code !== 200) {
        throw new Error(res.message || '登录失败')
      }
      t = res.data.token
      refreshTokenVal.value = res.data.refreshToken || t
      user = res.data.user
    } else {
      // Legacy bare format: { access_token, token_type, user }
      t = res.access_token || res.token || ''
      refreshTokenVal.value = res.refreshToken || t
      user = res.user || res.userInfo
    }

    if (!t) {
      throw new Error('登录响应缺少 token，请检查后端服务')
    }
    if (!user) {
      throw new Error('登录响应缺少用户信息，请检查后端服务')
    }

    token.value = t
    // Normalize legacy role values to 'admin' for the router guard
    const normalizedRole = ['super_admin', 'training_admin', 'instructor'].includes(user.role)
      ? 'admin'
      : user.role
    userInfo.value = {
      id: user.id,
      username: user.username,
      realName: user.real_name || user.realName || '',
      phone: user.phone || '',
      role: normalizedRole,
      storeId: user.store_id ?? user.storeId,
      status: user.is_active ?? user.status ? 1 : 0,
      createdAt: user.created_at || user.createdAt || '',
    }

    localStorage.setItem('auth-store', JSON.stringify({ token: t, role: normalizedRole }))
  }

  async function fetchUserInfo() {
    if (!token.value) return
    try {
      const res = await import('@/api/auth').then((m) => m.getUserInfo())
      userInfo.value = res
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    refreshTokenVal.value = ''
    userInfo.value = null
    localStorage.removeItem('auth-store')
    router.push('/login')
  }

  return { token, refreshTokenVal, userInfo, isLoggedIn, isAdmin, login, fetchUserInfo, logout }
})
