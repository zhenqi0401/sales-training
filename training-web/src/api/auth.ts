import http from './index'
import type { ApiResponse, UserInfo } from '@/types'

/**
 * Auth API
 */
export const authApi = {
  /**
   * Send SMS verification code
   */
  sendCode(phone: string) {
    return http.post<ApiResponse>('/auth/send-code', { phone })
  },

  /**
   * Login with phone + code
   */
  loginByPhone(phone: string, code: string) {
    return http.post<ApiResponse<{ token: string; refreshToken: string; user: UserInfo }>>('/auth/phone-login', {
      phone,
      code
    })
  },

  /**
   * Refresh token
   */
  refreshToken(refreshToken: string) {
    return http.post<ApiResponse<{ token: string; refreshToken: string }>>('/auth/refresh', {
      refreshToken
    })
  },

  /**
   * Get current user info
   */
  getUserInfo() {
    return http.get<ApiResponse<UserInfo>>('/auth/user-info')
  },

  /**
   * Update user profile
   */
  updateProfile(data: Partial<UserInfo>) {
    return http.put<ApiResponse<UserInfo>>('/auth/profile', data)
  },

  /**
   * Logout
   */
  logout() {
    return http.post<ApiResponse>('/auth/logout')
  }
}
