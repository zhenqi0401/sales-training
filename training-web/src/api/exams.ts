import http from './index'
import type { ApiResponse, ExamConfig, Question, ExamRecord, WrongAnswer, PaginatedData } from '@/types'

function unwrapResponse<T>(request: Promise<unknown>) {
  return request as Promise<ApiResponse<T>>
}

/**
 * Exam API
 */
export const examsApi = {
  /**
   * Get exam config by level
   */
  getExamConfig(level: string) {
    return unwrapResponse<ExamConfig>(http.get<ApiResponse<ExamConfig>>(`/exams/config/${level}`))
  },

  /**
   * Get exam questions
   */
  getQuestions(level: string) {
    return unwrapResponse<Question[]>(http.get<ApiResponse<Question[]>>(`/exams/questions/${level}`))
  },

  /**
   * Submit exam answers
   */
  submitExam(data: { paperId?: number; level: string; answers: Array<{ questionId: number; selected: string | string[] }>; duration: number }) {
    return unwrapResponse<ExamRecord>(http.post<ApiResponse<ExamRecord>>('/exams/submit', data))
  },

  /**
   * Get exam record
   */
  getExamRecord(recordId: number) {
    return unwrapResponse<ExamRecord>(http.get<ApiResponse<ExamRecord>>(`/exams/records/${recordId}`))
  },

  /**
   * Get exam history
   */
  getExamHistory(page = 1, pageSize = 10) {
    return unwrapResponse<PaginatedData<ExamRecord>>(http.get<ApiResponse<PaginatedData<ExamRecord>>>('/exams/records', {
      params: { page, pageSize }
    }))
  },

  /**
   * Get wrong answers book
   */
  getWrongAnswers(page = 1, pageSize = 20, params: { categoryId?: number; keyword?: string } = {}) {
    return unwrapResponse<PaginatedData<WrongAnswer>>(http.get<ApiResponse<PaginatedData<WrongAnswer>>>('/exams/wrong-answers', {
      params: { page, pageSize, category_id: params.categoryId, keyword: params.keyword }
    }))
  },

  /**
   * Get wrong answer statistics
   */
  getWrongAnswerStats() {
    return unwrapResponse<{ totalWrong: number; weakCategories: { name: string; count: number }[]; weakKnowledgePoints: { name: string; count: number }[] }>(
      http.get<ApiResponse<any>>('/exams/wrong-answers/stats')
    )
  },

  /**
   * Get exam score trend
   */
  getTrend() {
    return unwrapResponse<Array<{ recordId: number; score: number; passed: boolean; submittedAt: string }>>(
      http.get<ApiResponse<any>>('/exams/trend')
    )
  },

  /**
   * Get sprint mode questions (random mix)
   */
  getSprintQuestions() {
    return unwrapResponse<Question[]>(http.get<ApiResponse<Question[]>>('/exams/sprint'))
  }
}
