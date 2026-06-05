// ==================== User Types ====================
export interface UserInfo {
  id: number
  username: string
  realName: string
  avatar?: string
  email?: string
  phone?: string
  role: 'admin' | 'trainer' | 'student'
  storeId?: number
  storeName?: string
  status: 0 | 1
  createdAt: string
}

export interface LoginParams {
  username: string
  password: string
  captcha?: string
}

export interface LoginResult {
  token: string
  refreshToken: string
  userInfo: UserInfo
}

// ==================== Category Types ====================
export interface Category {
  id: number
  name: string
  parentId: number | null
  sort: number
  children?: Category[]
  videoCount?: number
  createdAt: string
}

// ==================== Video Types ====================
export interface Video {
  id: number
  title: string
  description: string
  categoryId: number
  categoryName?: string
  url: string
  coverUrl?: string
  duration: number
  fileSize: number
  status: 'draft' | 'published' | 'archived'
  viewCount: number
  required: boolean
  createdAt: string
  updatedAt: string
}

export interface VideoUploadParams {
  title: string
  description?: string
  categoryId: number
  url: string
  coverUrl?: string
  required?: boolean
}

// ==================== Question Types ====================
export type QuestionType = 'single' | 'multiple' | 'true_false' | 'fill_blank' | 'essay'
export type Difficulty = 'easy' | 'medium' | 'hard'

export interface Question {
  id: number
  type: QuestionType
  difficulty: Difficulty
  categoryId: number
  categoryName?: string
  content: string
  options: QuestionOption[]
  answer: string | string[]
  explanation?: string
  tags: string[]
  status: 'active' | 'disabled'
  createdAt: string
}

export interface QuestionOption {
  label: string
  value: string
}

export interface AiGenerateParams {
  categoryId: number
  count: number
  difficulty: Difficulty
  type: QuestionType
  topic?: string
}

// ==================== Exam Types ====================
export interface Exam {
  id: number
  title: string
  description?: string
  duration: number
  totalScore: number
  passScore: number
  type: 'manual' | 'random' | 'ai'
  questionCount: number
  status: 'draft' | 'published' | 'closed'
  startTime?: string
  endTime?: string
  createdAt: string
}

export interface ExamQuestion {
  id: number
  examId: number
  questionId: number
  score: number
  sort: number
  question?: Question
}

// ==================== Store Types ====================
export interface Store {
  id: number
  name: string
  code: string
  address?: string
  phone?: string
  manager?: string
  status: 0 | 1
  createdAt: string
}

// ==================== Sales Script Types ====================
export interface SalesScript {
  id: number
  title: string
  category: string
  content: string
  tags: string[]
  status: 'published' | 'draft'
  createdAt: string
  updatedAt: string
}

// ==================== Product Knowledge Types ====================
export interface ProductKnowledge {
  id: number
  title: string
  brand?: string
  category: string
  content: string
  coverUrl?: string
  tags: string[]
  status: 'published' | 'draft'
  createdAt: string
  updatedAt: string
}

// ==================== Dashboard Types ====================
export interface DashboardStats {
  totalUsers: number
  activeUsers: number
  totalVideos: number
  examPassRate: number
  totalStores: number
  totalQuestions: number
  todayLogins: number
  completionRate: number
}

export interface ChartData {
  date: string
  value: number
}

// ==================== Common API Types ====================
export interface PageParams {
  page: number
  pageSize: number
}

export interface PageResult<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}
