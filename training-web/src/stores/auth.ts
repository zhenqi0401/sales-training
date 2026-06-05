import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref<string>('')
  const refreshToken = ref<string>('')
  const user = ref<UserInfo | null>(null)

  // Getters
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const userName = computed(() => user.value?.name ?? '')
  const userPhone = computed(() => user.value?.phone ?? '')
  const userAvatar = computed(() => user.value?.avatar ?? '')
  const storeName = computed(() => user.value?.storeName ?? '')

  // Actions
  function setToken(newToken: string, newRefreshToken: string) {
    token.value = newToken
    refreshToken.value = newRefreshToken
    localStorage.setItem('auth-token', newToken)
    localStorage.setItem('auth-refresh-token', newRefreshToken)
  }

  function setUser(userInfo: UserInfo) {
    user.value = userInfo
  }

  async function login(phone: string, code: string) {
    const res = await authApi.loginByPhone(phone, code)
    const data = res.data
    setToken(data.token, data.refreshToken)
    setUser(data.user)
    return data.user
  }

  async function fetchUserInfo() {
    try {
      const res = await authApi.getUserInfo()
      setUser(res.data)
    } catch {
      // If token is invalid, clear auth state
      logout()
    }
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('auth-token')
    localStorage.removeItem('auth-refresh-token')
  }

  // Restore token from localStorage on init
  function init() {
    const savedToken = localStorage.getItem('auth-token')
    const savedRefreshToken = localStorage.getItem('auth-refresh-token')
    if (savedToken) {
      token.value = savedToken
    }
    if (savedRefreshToken) {
      refreshToken.value = savedRefreshToken
    }
  }

  init()

  return {
    token,
    refreshToken,
    user,
    isLoggedIn,
    userName,
    userPhone,
    userAvatar,
    storeName,
    setToken,
    setUser,
    login,
    fetchUserInfo,
    logout,
    init
  }
})
