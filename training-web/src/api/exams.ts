import http from './index'
import type { ApiResponse, ExamConfig, Question, ExamRecord, WrongAnswer, PaginatedData } from '@/types'

/**
 * Exam API
 */
export const examsApi = {
  /**
   * Get exam config by level
   */
  getExamConfig(level: string) {
    return http.get<ApiResponse<ExamConfig>>(`/exams/config/${level}`)
  },

  /**
   * Get exam questions
   */
  getQuestions(level: string) {
    return http.get<ApiResponse<Question[]>>(`/exams/questions/${level}`)
  },

  /**
   * Submit exam answers
   */
  submitExam(data: { level: string; answers: Array<{ questionId: number; selected: string | string[] }>; duration: number }) {
    return http.post<ApiResponse<ExamRecord>>('/exams/submit', data)
  },

  /**
   * Get exam record
   */
  getExamRecord(recordId: number) {
    return http.get<ApiResponse<ExamRecord>>(`/exams/records/${recordId}`)
  },

  /**
   * Get exam history
   */
  getExamHistory(page = 1, pageSize = 10) {
    return http.get<ApiResponse<PaginatedData<ExamRecord>>>('/exams/records', {
      params: { page, pageSize }
    })
  },

  /**
   * Get wrong answers book
   */
  getWrongAnswers(page = 1, pageSize = 20) {
    return http.get<ApiResponse<PaginatedData<WrongAnswer>>>('/exams/wrong-answers', {
      params: { page, pageSize }
    })
  },

  /**
   * Get sprint mode questions (random mix)
   */
  getSprintQuestions() {
    return http.get<ApiResponse<Question[]>>('/exams/sprint')
  }
}
