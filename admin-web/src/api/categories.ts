import { get, post, put, del } from './index'
import type { Category, PageResult } from '@/types'

type BackendPage<T> = PageResult<T> & { items?: T[] }

function normalizeCategory(data: any): Category {
  return {
    ...data,
    parentId: data.parentId ?? data.parent_id ?? null,
    sort: data.sort ?? data.sort_order ?? 0,
    videoCount: data.videoCount ?? data.video_count ?? 0,
    createdAt: data.createdAt ?? data.created_at ?? '',
    children: Array.isArray(data.children) ? data.children.map(normalizeCategory) : data.children,
  }
}

function toCategoryPayload(params: Partial<Category> & { parentId?: number | null; sort?: number }): Record<string, any> {
  return {
    ...params,
    parent_id: params.parentId,
    sort_order: params.sort,
  }
}

export function getCategoryList(): Promise<Category[]> {
  return get<BackendPage<any>>('/categories/').then((res) => (res.list ?? res.items ?? []).map(normalizeCategory))
}

export function getCategoryTree(): Promise<Category[]> {
  return get<any[]>('/categories/tree').then((items) => items.map(normalizeCategory))
}

export function createCategory(params: { name: string; parentId?: number | null; sort?: number }): Promise<Category> {
  return post<any>('/categories/', toCategoryPayload(params)).then(normalizeCategory)
}

export function updateCategory(id: number, params: Partial<Category>): Promise<Category> {
  return put<any>(`/categories/${id}`, toCategoryPayload(params)).then(normalizeCategory)
}

export function deleteCategory(id: number): Promise<void> {
  return del<void>(`/categories/${id}`)
}
