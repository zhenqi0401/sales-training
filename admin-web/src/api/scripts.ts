import { get, post, put, del } from './index'
import type { SalesScript, PageResult } from '@/types'

type BackendPage<T> = PageResult<T> & { items?: T[] }
export interface ScriptCategoryOption {
  value: string
  label: string
  count: number
}
type EditableScript = Omit<Partial<SalesScript>, 'status'> & { status?: string }

function normalizeScript(data: any): SalesScript {
  return {
    ...data,
    tags: Array.isArray(data.tags) ? data.tags : [],
    status: data.status ?? (data.is_active === false ? 'draft' : 'published'),
    createdAt: data.createdAt ?? data.created_at ?? '',
    updatedAt: data.updatedAt ?? data.updated_at ?? data.created_at ?? '',
  }
}

function normalizeScriptPage(data: BackendPage<any>): PageResult<SalesScript> {
  return {
    ...data,
    list: (data.list ?? data.items ?? []).map(normalizeScript),
  }
}

function toScriptPayload(params: EditableScript): Record<string, any> {
  return {
    title: params.title,
    category: params.category,
    content: params.content,
    tags: params.tags,
    is_active: params.status ? params.status === 'published' : undefined,
  }
}

export function getScriptList(params: {
  page: number
  pageSize: number
  category?: string
  status?: string
  keyword?: string
}): Promise<PageResult<SalesScript>> {
  return get<BackendPage<any>>('/scripts/', params).then(normalizeScriptPage)
}

export function getScriptCategoryOptions(): Promise<ScriptCategoryOption[]> {
  return get<ScriptCategoryOption[]>('/scripts/categories')
}

export function getScriptDetail(id: number): Promise<SalesScript> {
  return get<any>(`/scripts/${id}`).then(normalizeScript)
}

export function createScript(params: EditableScript): Promise<SalesScript> {
  return post<any>('/scripts/', toScriptPayload(params)).then(normalizeScript)
}

export function updateScript(id: number, params: EditableScript): Promise<SalesScript> {
  return put<any>(`/scripts/${id}`, toScriptPayload(params)).then(normalizeScript)
}

export function deleteScript(id: number): Promise<void> {
  return del<void>(`/scripts/${id}`)
}
