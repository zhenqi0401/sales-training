import { get, post, put, del } from './index'
import type { Store, PageResult } from '@/types'

export function getStoreList(params?: {
  page?: number
  pageSize?: number
  keyword?: string
  status?: number
}): Promise<PageResult<Store>> {
  return get<PageResult<Store>>('/stores/', params)
}

export function getAllStores(): Promise<Store[]> {
  return get<Store[]>('/stores/all')
}

export function createStore(params: Partial<Store>): Promise<Store> {
  return post<Store>('/stores/', params)
}

export function updateStore(id: number, params: Partial<Store>): Promise<Store> {
  return put<Store>(`/stores/${id}`, params)
}

export function deleteStore(id: number): Promise<void> {
  return del<void>(`/stores/${id}`)
}

export function toggleStoreStatus(id: number, status: 0 | 1): Promise<Store> {
  return put<Store>(`/stores/${id}/status`, { status })
}
