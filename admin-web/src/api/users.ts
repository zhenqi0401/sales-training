import { get, post, put, del } from './index'
import type { UserInfo, PageResult } from '@/types'

type BackendUser = Record<string, any>
type BackendPage<T> = PageResult<T> & {
  items?: T[]
  page_size?: number
}

function normalizeUser(data: BackendUser): UserInfo {
  return {
    id: data.id,
    username: data.username || '',
    realName: data.realName ?? data.real_name ?? '',
    avatar: data.avatar || '',
    email: data.email || '',
    phone: data.phone || '',
    role: data.role,
    storeId: data.storeId ?? data.store_id ?? undefined,
    storeName: data.storeName ?? data.store_name ?? '',
    status: data.status ?? (data.is_active === false ? 0 : 1),
    createdAt: data.createdAt ?? data.created_at ?? '',
  }
}

function normalizeUserPage(data: BackendPage<BackendUser>): PageResult<UserInfo> {
  const list = data.list ?? data.items ?? []
  return {
    list: list.map(normalizeUser),
    total: data.total || 0,
    page: data.page || 1,
    pageSize: data.pageSize ?? data.page_size ?? list.length,
  }
}

function cleanPayload(data: Record<string, any>): Record<string, any> {
  return Object.fromEntries(
    Object.entries(data).filter(([, value]) => value !== undefined && value !== null && value !== ''),
  )
}

function toUserPayload(params: Partial<UserInfo> & { password?: string }): Record<string, any> {
  return cleanPayload({
    username: params.username,
    phone: params.phone,
    password: params.password,
    real_name: params.realName,
    role: params.role,
    store_id: params.storeId,
    is_active: params.status === undefined ? undefined : params.status === 1,
  })
}

export function getUserList(params: {
  page: number
  pageSize: number
  role?: string
  status?: number
  keyword?: string
  storeId?: number
}): Promise<PageResult<UserInfo>> {
  return get<BackendPage<BackendUser>>('/users/', params).then(normalizeUserPage)
}

export function getUserDetail(id: number): Promise<UserInfo & {
  videoProgress: any[]
  examRecords: any[]
  loginHistory: any[]
}> {
  return get<BackendUser>(`/users/${id}`).then((data) => ({
    ...normalizeUser(data),
    videoProgress: data.videoProgress || data.video_progress || [],
    examRecords: data.examRecords || data.exam_records || [],
    loginHistory: data.loginHistory || data.login_history || [],
  }))
}

export function createUser(params: Partial<UserInfo> & { password: string }): Promise<UserInfo> {
  return post<BackendUser>('/users/', toUserPayload(params)).then(normalizeUser)
}

export function updateUser(id: number, params: Partial<UserInfo>): Promise<UserInfo> {
  return put<BackendUser>(`/users/${id}`, toUserPayload(params)).then(normalizeUser)
}

export function deleteUser(id: number): Promise<void> {
  return del<void>(`/users/${id}`)
}

export function batchImportUsers(users: Array<{ username: string; password: string; realName: string; role: string; phone?: string }>): Promise<number> {
  return post<number>('/users/batch-import', {
    users: users.map((user) => toUserPayload(user as Partial<UserInfo> & { password: string })),
  })
}

export function resetUserPassword(id: number, password: string): Promise<void> {
  return put<void>(`/users/${id}/password`, { password })
}

export function toggleUserStatus(id: number, status: 0 | 1): Promise<UserInfo> {
  return updateUser(id, { status })
}

export function getUserProgress(id: number): Promise<any[]> {
  return get<any[]>(`/users/${id}/progress`)
}

export function getUserExamRecords(id: number): Promise<any[]> {
  return get<any[]>(`/users/${id}/exam-records`)
}
