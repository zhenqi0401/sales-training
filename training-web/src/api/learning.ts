import http from './index'
import type {
  CalendarDay,
  Announcement,
  ApiResponse,
  Category,
  Video,
  LearningProgress,
  DailyTask,
  LeaderboardEntry,
  LearningStats
} from '@/types'

export type LeaderboardPeriod = 'day' | 'week' | 'month'

function unwrapResponse<T>(request: Promise<unknown>) {
  return request as Promise<ApiResponse<T>>
}

/**
 * Learning API — videos, categories, progress
 */
export const learningApi = {
  /**
   * Get all course categories
   */
  getCategories() {
    return unwrapResponse<Category[]>(http.get<ApiResponse<Category[]>>('/learning/categories'))
  },

  /**
   * Get videos by category
   */
  getVideosByCategory(categoryId: number) {
    return unwrapResponse<Video[]>(http.get<ApiResponse<Video[]>>(`/learning/categories/${categoryId}/videos`))
  },

  /**
   * Get video detail
   */
  getVideoDetail(videoId: number) {
    return unwrapResponse<Video>(http.get<ApiResponse<Video>>(`/learning/videos/${videoId}`))
  },

  /**
   * Submit learning progress
   */
  updateProgress(data: { videoId: number; watchDuration: number; progress: number; completed: boolean }) {
    return unwrapResponse<LearningProgress>(http.post<ApiResponse<LearningProgress>>('/learning/progress', {
      videoId: data.videoId,
      watchDuration: data.watchDuration,
      lastPosition: data.watchDuration,
      progress: data.progress,
      completed: data.completed,
      status: data.completed ? 'completed' : 'in_progress'
    }))
  },

  /**
   * Get learning progress for a video
   */
  getProgress(videoId: number) {
    return unwrapResponse<LearningProgress>(http.get<ApiResponse<LearningProgress>>(`/learning/progress/${videoId}`))
  },

  /**
   * Get daily tasks
   */
  getDailyTasks() {
    return unwrapResponse<DailyTask[]>(http.get<ApiResponse<DailyTask[]>>('/learning/daily-tasks'))
  },

  /**
   * Complete daily task
   */
  completeTask(taskId: number) {
    return unwrapResponse(http.post<ApiResponse>(`/learning/daily-tasks/${taskId}/complete`))
  },

  /**
   * Get recently watched courses
   */
  getRecentCourses() {
    return unwrapResponse<Video[]>(http.get<ApiResponse<Video[]>>('/learning/recent'))
  },

  /**
   * Get leaderboard
   */
  getLeaderboard(period: LeaderboardPeriod = 'week') {
    return unwrapResponse<LeaderboardEntry[]>(http.get<ApiResponse<LeaderboardEntry[]>>('/learning/leaderboard', {
      params: { period }
    }))
  },

  /**
   * Get announcements
   */
  getAnnouncements() {
    return unwrapResponse<Announcement[]>(http.get<ApiResponse<Announcement[]>>('/learning/announcements'))
  },

  /**
   * Get user learning stats
   */
  getLearningStats() {
    return unwrapResponse<LearningStats>(http.get<ApiResponse<LearningStats>>('/learning/stats'))
  },

  /**
   * Get learning calendar heatmap data
   */
  getCalendar(days: number = 84) {
    return unwrapResponse<CalendarDay[]>(http.get<ApiResponse<CalendarDay[]>>('/learning/calendar', {
      params: { days }
    }))
  },

  /**
   * Get training scripts list with categories
   */
  getScripts(category?: string, page: number = 1, pageSize: number = 50, favorites: boolean = false) {
    return unwrapResponse<{ items: any[]; total: number; categories: { code: string; name: string; count: number }[] }>(
      http.get<ApiResponse<any>>('/learning/scripts', {
        params: { category, page, pageSize, favorites }
      })
    )
  },

  /**
   * Get single script detail
   */
  getScriptDetail(id: number) {
    return unwrapResponse<any>(http.get<ApiResponse<any>>(`/learning/scripts/${id}`))
  },

  /**
   * Toggle script favorite (add or remove)
   */
  toggleScriptFavorite(scriptId: number, isFavorite: boolean) {
    if (isFavorite) {
      return unwrapResponse<void>(http.delete<ApiResponse>(`/favorites/?type=script&target_id=${scriptId}`))
    }
    return unwrapResponse<void>(http.post<ApiResponse>('/favorites/', { type: 'script', target_id: scriptId }))
  }
}
