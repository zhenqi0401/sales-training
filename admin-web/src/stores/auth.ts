import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { post } from '@/api/index'
import type { UserInfo } from '@/types'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  // ---- State ----
  const token = ref<string>('')
  const refreshTokenVal = ref<string>('')
  const userInfo = ref<UserInfo | null>(null)

  // ---- Getters ----
  const isLoggedIn = computed(() => !!token.value)

  // ---- Actions ----
  async function login(username: string, password: string) {
    // Only send fields the backend expects (LoginRequest: username, password)
    const res = await post('/auth/login', { username, password })
    const t = res.access_token as string

    token.value = t
    refreshTokenVal.value = t
    userInfo.value = {
      id: res.user.id,
      username: res.user.username,
      realName: res.user.real_name || '',
      phone: res.user.phone || '',
      role: res.user.role,
      storeId: res.user.store_id,
      status: res.user.is_active ? 1 : 0,
      createdAt: res.user.created_at || '',
    }

    // Immediately persist so the axios interceptor sees it
    localStorage.setItem('auth-store', JSON.stringify({
      token: t,
    }))
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

  return { token, refreshTokenVal, userInfo, isLoggedIn, login, fetchUserInfo, logout }
}, {
  persist: false, // Disable Pinia persist — we handle localStorage ourselves
})
