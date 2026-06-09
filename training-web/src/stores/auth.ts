import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types'
import { authApi } from '@/api/auth'

const AUTH_TOKEN_REFRESHED_EVENT = 'auth-token-refreshed'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref<string>('')
  const refreshToken = ref<string>('')
  const user = ref<UserInfo | null>(null)

  // Getters
  const isLoggedIn = computed(() => !!token.value)
  const userName = computed(() => user.value?.name ?? '')
  const userPhone = computed(() => user.value?.phone ?? '')
  const userAvatar = computed(() => user.value?.avatar ?? '')
  const storeName = computed(() => user.value?.storeName ?? '')
  const mustChangePassword = computed(() => user.value?.mustChangePassword === true)

  // Actions
  function setToken(newToken: string, newRefreshToken: string) {
    token.value = newToken
    refreshToken.value = newRefreshToken
    localStorage.setItem('auth-token', newToken)
    localStorage.setItem('auth-refresh-token', newRefreshToken)
  }

  function setUser(userInfo: UserInfo) {
    user.value = userInfo
    localStorage.setItem('auth-user', JSON.stringify(userInfo))
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
      return res.data
    } catch {
      // If token is invalid, clear auth state
      logout()
      return null
    }
  }

  async function initPassword(newPassword: string) {
    const res = await authApi.initPassword(newPassword)
    setUser(res.data)
    return res.data
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('auth-token')
    localStorage.removeItem('auth-refresh-token')
    localStorage.removeItem('auth-user')
  }

  function syncRefreshedToken(event: Event) {
    const detail = (event as CustomEvent<{ token?: string; refreshToken?: string }>).detail
    if (!detail?.token) return
    token.value = detail.token
    if (detail.refreshToken) {
      refreshToken.value = detail.refreshToken
    }
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
    const savedUser = localStorage.getItem('auth-user')
    if (savedUser) {
      try {
        user.value = JSON.parse(savedUser)
      } catch {
        localStorage.removeItem('auth-user')
      }
    }
  }

  init()

  if (typeof window !== 'undefined') {
    window.addEventListener(AUTH_TOKEN_REFRESHED_EVENT, syncRefreshedToken)
  }

  return {
    token,
    refreshToken,
    user,
    isLoggedIn,
    userName,
    userPhone,
    userAvatar,
    storeName,
    mustChangePassword,
    setToken,
    setUser,
    login,
    initPassword,
    fetchUserInfo,
    logout,
    init
  }
})
