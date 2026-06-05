import { get, post, put, del } from './index'
import type { UserInfo, PageResult } from '@/types'

export function getUserList(params: {
  page: number
  pageSize: number
  role?: string
  status?: number
  keyword?: string
  storeId?: number
}): Promise<PageResult<UserInfo>> {
  return get<PageResult<UserInfo>>('/users/', params)
}

export function getUserDetail(id: number): Promise<UserInfo & {
  videoProgress: any[]
  examRecords: any[]
  loginHistory: any[]
}> {
  return get<UserInfo & {
    videoProgress: any[]
    examRecords: any[]
    loginHistory: any[]
  }>(`/users/${id}`)
}

export function createUser(params: Partial<UserInfo> & { password: string }): Promise<UserInfo> {
  return post<UserInfo>('/users/', params)
}

export function updateUser(id: number, params: Partial<UserInfo>): Promise<UserInfo> {
  return put<UserInfo>(`/users/${id}`, params)
}

export function deleteUser(id: number): Promise<void> {
  return del<void>(`/users/${id}`)
}

export function batchImportUsers(users: Array<{ username: string; password: string; realName: string; role: string }>): Promise<number> {
  return post<number>('/users/batch-import', { users })
}

export function resetUserPassword(id: number, password: string): Promise<void> {
  return put<void>(`/users/${id}/password`, { password })
}

export function toggleUserStatus(id: number, status: 0 | 1): Promise<UserInfo> {
  return put<UserInfo>(`/users/${id}/status`, { status })
}

export function getUserProgress(id: number): Promise<any[]> {
  return get<any[]>(`/users/${id}/progress`)
}

export function getUserExamRecords(id: number): Promise<any[]> {
  return get<any[]>(`/users/${id}/exam-records`)
}
