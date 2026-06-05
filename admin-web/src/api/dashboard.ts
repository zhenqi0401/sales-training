import { get } from './index'
import type { DashboardStats } from '@/types'

export function getDashboardStats(): Promise<DashboardStats> {
  // Snake_case from backend normalized to camelCase by the interceptor.
  // Backend returns: total_users, active_users, total_videos, total_questions,
  //   total_stores, total_exams, exam_pass_rate, completion_rate
  return get<DashboardStats>('/dashboard/admin-overview')
}
