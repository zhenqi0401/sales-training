import http from './index'
import type { ApiResponse, Category, Video, LearningProgress, DailyTask, LeaderboardEntry } from '@/types'

/**
 * Learning API — videos, categories, progress
 */
export const learningApi = {
  /**
   * Get all course categories
   */
  getCategories() {
    return http.get<ApiResponse<Category[]>>('/learning/categories')
  },

  /**
   * Get videos by category
   */
  getVideosByCategory(categoryId: number) {
    return http.get<ApiResponse<Video[]>>(`/learning/categories/${categoryId}/videos`)
  },

  /**
   * Get video detail
   */
  getVideoDetail(videoId: number) {
    return http.get<ApiResponse<Video>>(`/learning/videos/${videoId}`)
  },

  /**
   * Submit learning progress
   */
  updateProgress(data: { videoId: number; watchDuration: number; progress: number; completed: boolean }) {
    return http.post<ApiResponse<LearningProgress>>('/learning/progress', data)
  },

  /**
   * Get learning progress for a video
   */
  getProgress(videoId: number) {
    return http.get<ApiResponse<LearningProgress>>(`/learning/progress/${videoId}`)
  },

  /**
   * Get daily tasks
   */
  getDailyTasks() {
    return http.get<ApiResponse<DailyTask[]>>('/learning/daily-tasks')
  },

  /**
   * Complete daily task
   */
  completeTask(taskId: number) {
    return http.post<ApiResponse>(`/learning/daily-tasks/${taskId}/complete`)
  },

  /**
   * Get leaderboard
   */
  getLeaderboard() {
    return http.get<ApiResponse<LeaderboardEntry[]>>('/learning/leaderboard')
  },

  /**
   * Get user learning stats
   */
  getLearningStats() {
    return http.get<ApiResponse<{
      totalVideos: number
      completedVideos: number
      totalDuration: number
      todayDuration: number
      streakDays: number
    }>>('/learning/stats')
  }
}
