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
    const res = await post<LoginResult & { access_token?: string; user?: any }>('/auth/login', { username, password })
    const t = (res.access_token || res.token) as string
    const user = res.user || res.userInfo

    token.value = t
    refreshTokenVal.value = res.refreshToken || t
    userInfo.value = {
      id: user.id,
      username: user.username,
      realName: user.real_name || user.realName || '',
      phone: user.phone || '',
      role: user.role,
      storeId: user.store_id ?? user.storeId,
      status: user.is_active ?? user.status ? 1 : 0,
      createdAt: user.created_at || user.createdAt || '',
    }

    localStorage.setItem('auth-store', JSON.stringify({ token: t, role: user.role }))
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
