import { get } from './index'
import type { UserInfo } from '@/types'

export function getUserInfo(): Promise<UserInfo> {
  return get<UserInfo>('/auth/me')
}
