import { get, post, put, del } from './index'
import type { Exam, ExamQuestion, PageResult } from '@/types'

export function getExamList(params: {
  page: number
  pageSize: number
  status?: string
  keyword?: string
}): Promise<PageResult<Exam>> {
  return get<PageResult<Exam>>('/exams', params)
}

export function getExamDetail(id: number): Promise<Exam & { questions: ExamQuestion[] }> {
  return get<Exam & { questions: ExamQuestion[] }>(`/exams/${id}`)
}

export function createExam(params: Partial<Exam>): Promise<Exam> {
  return post<Exam>('/exams', params)
}

export function updateExam(id: number, params: Partial<Exam>): Promise<Exam> {
  return put<Exam>(`/exams/${id}`, params)
}

export function deleteExam(id: number): Promise<void> {
  return del<void>(`/exams/${id}`)
}

export function publishExam(id: number): Promise<Exam> {
  return put<Exam>(`/exams/${id}/publish`, {})
}

export function closeExam(id: number): Promise<Exam> {
  return put<Exam>(`/exams/${id}/close`, {})
}

export function getExamQuestions(id: number): Promise<ExamQuestion[]> {
  return get<ExamQuestion[]>(`/exams/${id}/questions`)
}

export function addExamQuestion(examId: number, questionId: number, score: number): Promise<ExamQuestion> {
  return post<ExamQuestion>(`/exams/${examId}/questions`, { questionId, score })
}

export function updateExamQuestion(id: number, score: number): Promise<void> {
  return put<void>(`/exams/questions/${id}`, { score })
}

export function removeExamQuestion(id: number): Promise<void> {
  return del<void>(`/exams/questions/${id}`)
}

export function randomSelectQuestions(examId: number, count: number, categories: number[]): Promise<ExamQuestion[]> {
  return post<ExamQuestion[]>(`/exams/${examId}/random`, { count, categories })
}
