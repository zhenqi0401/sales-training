import { get } from './index'
import type { ApiResponse } from '@/types'

export interface SalesUser {
  id: number
  username: string
  real_name: string
  avatar: string
  phone: string
  sales_count: number
  deal_count: number
  methodology_count: number
  methodologies: Methodology[]
}

export interface Methodology {
  id: number
  title: string
  content: string
  source: string
  created_at: string
}

export function getSalesList(): Promise<ApiResponse<SalesUser[]>> {
  return get<ApiResponse<SalesUser[]>>('/sales/admin/sales-list')
}
