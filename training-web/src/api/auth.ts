import http from './index'
import type { ApiResponse, UserInfo } from '@/types'

type PhoneLoginData = { token: string; refreshToken: string; user: UserInfo }

function unwrapResponse<T>(request: Promise<unknown>) {
  return request as Promise<ApiResponse<T>>
}

/**
 * Auth API
 */
export const authApi = {
  /**
   * Send SMS verification code
   */
  sendCode(phone: string) {
    return unwrapResponse(http.post<ApiResponse>('/auth/send-code', { phone }))
  },

  /**
   * Login with phone + code
   */
  loginByPhone(phone: string, code: string) {
    return unwrapResponse<PhoneLoginData>(http.post<ApiResponse<PhoneLoginData>>('/auth/phone-login', {
      phone,
      code
    }))
  },

  /**
   * Refresh token
   */
  refreshToken(refreshToken: string) {
    return unwrapResponse<{ token: string; refreshToken: string }>(http.post<ApiResponse<{ token: string; refreshToken: string }>>('/auth/refresh', {
      refreshToken
    }))
  },

  /**
   * Get current user info
   */
  getUserInfo() {
    return unwrapResponse<UserInfo>(http.get<ApiResponse<UserInfo>>('/auth/user-info'))
  },

  /**
   * Update user profile
   */
  updateProfile(data: Partial<UserInfo>) {
    return unwrapResponse<UserInfo>(http.put<ApiResponse<UserInfo>>('/auth/profile', data))
  },

  /**
   * Set password after first SMS login
   */
  initPassword(newPassword: string) {
    return unwrapResponse<UserInfo>(http.post<ApiResponse<UserInfo>>('/auth/init-password', {
      new_password: newPassword
    }))
  },

  /**
   * Logout
   */
  logout() {
    return unwrapResponse(http.post<ApiResponse>('/auth/logout'))
  }
}
