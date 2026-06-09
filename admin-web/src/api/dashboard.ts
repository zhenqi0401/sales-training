import { get } from './index'
import request from './index'
import type { DashboardData, DashboardStats } from '@/types'

export function getDashboardStats(): Promise<DashboardStats> {
  // Snake_case from backend normalized to camelCase by the interceptor.
  // Backend returns: total_users, active_users, total_videos, total_questions,
  //   total_stores, total_exams, exam_pass_rate, completion_rate
  return get<DashboardStats>('/dashboard/admin-overview')
}

export function getDashboardData(): Promise<DashboardData> {
  return get<DashboardData>('/dashboard/admin-overview')
}

export async function exportStudentProgress(): Promise<void> {
  const response = await request.get('/dashboard/student-progress-export', {
    responseType: 'blob',
  })
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'student-progress.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
