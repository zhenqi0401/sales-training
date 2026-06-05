import { get, post, put, del } from './index'
import type { ProductKnowledge, PageResult } from '@/types'

type BackendPage<T> = PageResult<T> & { items?: T[] }
export interface ProductCategoryOption {
  id: number
  code: string
  name: string
  count: number
}
type EditableProduct = Omit<Partial<ProductKnowledge>, 'status'> & { status?: string }

function normalizeProduct(data: any): ProductKnowledge {
  const specs = data.specs && typeof data.specs === 'object' ? data.specs : {}

  return {
    ...data,
    title: data.title ?? data.name ?? '',
    brand: data.brand ?? specs.brand ?? '',
    category: data.category ?? data.category_code ?? specs.category ?? String(data.category_id ?? ''),
    categoryName: data.categoryName ?? data.category_name ?? specs.category_name,
    content: data.content ?? data.intro ?? '',
    coverUrl: data.coverUrl ?? data.cover_url ?? specs.coverUrl ?? specs.cover_url,
    tags: Array.isArray(data.tags) ? data.tags : Array.isArray(specs.tags) ? specs.tags : [],
    status: data.status ?? (data.is_active === false ? 'draft' : 'published'),
    createdAt: data.createdAt ?? data.created_at ?? '',
    updatedAt: data.updatedAt ?? data.updated_at ?? data.created_at ?? '',
  }
}

function normalizeProductPage(data: BackendPage<any>): PageResult<ProductKnowledge> {
  return {
    ...data,
    list: (data.list ?? data.items ?? []).map(normalizeProduct),
  }
}

function toProductPayload(params: EditableProduct): Record<string, any> {
  return {
    name: params.title,
    intro: params.content,
    category: params.category,
    specs: {
      brand: params.brand,
      category: params.category,
      tags: params.tags,
      coverUrl: params.coverUrl,
    },
    is_active: params.status ? params.status === 'published' : undefined,
  }
}

export function getProductList(params: {
  page: number
  pageSize: number
  category?: string
  brand?: string
  status?: string
  keyword?: string
}): Promise<PageResult<ProductKnowledge>> {
  return get<BackendPage<any>>('/products/', params).then(normalizeProductPage)
}

export function getProductCategoryOptions(): Promise<ProductCategoryOption[]> {
  return get<ProductCategoryOption[]>('/products/categories')
}

export function getProductDetail(id: number): Promise<ProductKnowledge> {
  return get<any>(`/products/${id}`).then(normalizeProduct)
}

export function createProduct(params: EditableProduct): Promise<ProductKnowledge> {
  return post<any>('/products/', toProductPayload(params)).then(normalizeProduct)
}

export function updateProduct(id: number, params: EditableProduct): Promise<ProductKnowledge> {
  return put<any>(`/products/${id}`, toProductPayload(params)).then(normalizeProduct)
}

export function deleteProduct(id: number): Promise<void> {
  return del<void>(`/products/${id}`)
}
