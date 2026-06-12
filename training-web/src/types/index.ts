// TypeScript type definitions for training-web

// ===== User & Auth =====
export interface UserInfo {
  id: number
  name: string
  phone: string
  avatar: string
  storeName: string
  joinDate: string
  level: number
  point: number
  mustChangePassword?: boolean
  role?: string
}

export interface AuthState {
  token: string
  refreshToken: string
  user: UserInfo | null
  isLoggedIn: boolean
}

// ===== Learning =====
export interface Category {
  id: number
  code: string
  name: string
  icon: string
  description: string
  videoCount: number
  completedCount: number
  sort: number
}

export interface Video {
  id: number
  categoryId: number
  title: string
  cover: string
  url: string
  duration: number // seconds
  watchDuration: number // seconds watched
  completed: boolean
  progress: number // 0-100
  description: string
  resolution?: string
  讲师: string
  createdAt: string
  required?: boolean
  estDuration?: number
}

export interface LearningProgress {
  videoId: number
  progress: number // 0-100
  watchDuration: number
  completed: boolean
  lastWatchTime: string
}

export interface LearningStats {
  totalVideos: number
  completedVideos: number
  inProgressVideos: number
  pendingVideos: number
  totalDuration: number
  todayDuration: number
  streakDays: number
}

export interface Announcement {
  id: number
  title: string
  content: string
  type: 'task' | 'ranking' | 'system' | 'course'
  publishedAt: string
  read: boolean
}

export interface CalendarDay {
  date: string       // YYYY-MM-DD
  duration: number   // seconds studied that day
  completed: number  // videos completed that day
}

// ===== Practice Modules =====
export interface PracticeModule {
  id: number
  code: string
  title: string
  description: string
  icon: string
  category: string
  sort: number
}

export interface PracticeContent {
  id: number
  moduleId: number
  type: 'knowledge' | 'dialogue' | 'quiz' | 'simulation'
  title: string
  content: string
  data: Record<string, any>
}

// ===== Sales Scripts =====
export interface ScriptCategory {
  id: number
  name: string
  masterTheory: string
  description: string
  scriptCount: number
}

export interface SalesScript {
  id: number
  categoryId: number
  title: string
  content: string
  summary: string
  tags: string[]
  isFavorite: boolean
  createdAt: string
}

// ===== Products =====
export interface ProductCategory {
  id: number
  name: string
  icon: string
  productCount: number
}

export interface Product {
  id: number
  categoryId: number
  name: string
  brand: string
  image: string
  specs: ProductSpec[]
  faq: ProductFAQ[]
  description: string
  sellingPoints: string[]
}

export interface ProductSpec {
  label: string
  value: string
}

export interface ProductFAQ {
  question: string
  answer: string
}

// ===== Exam =====
export type ExamLevel = 'L1' | 'L2' | 'L3' | 'SPRINT' | 'WRONG'
export type QuestionType = 'single' | 'multi' | 'judge'

export interface ExamConfig {
  level: ExamLevel
  paperId?: number
  title: string
  description: string
  questionCount: number
  duration: number // minutes
  passScore: number
  totalScore: number
}

export interface Question {
  id: number
  examLevel: ExamLevel
  type: QuestionType
  content: string
  options: QuestionOption[]
  answer: string | string[]
  score: number
  analysis: string
  knowledgePoint: string
  categoryId?: number
  categoryName?: string
  tags?: string[]
}

export interface QuestionOption {
  label: string
  value: string
  content: string
}

export interface ExamRecord {
  id: number
  examLevel: ExamLevel
  paperId?: number
  paperTitle?: string
  score: number
  totalScore: number
  passScore?: number
  passed: boolean
  duration: number
  correctCount: number
  totalCount: number
  submittedAt: string
  answers: UserAnswer[]
  categoryScores?: CategoryScore[]
  weakPoints?: string[]
}

export interface UserAnswer {
  questionId: number
  question?: Question
  selected: string | string[]
  userAnswer?: string
  correct: boolean
  isCorrect?: boolean
  correctAnswer?: string
  score: number
  analysis?: string
  knowledgePoint?: string
}

export interface CategoryScore {
  category: string
  score: number
  totalScore: number
  correctCount: number
  totalCount: number
}

export interface WrongAnswer {
  id: number
  question: Question
  userAnswer: string | string[]
  examId: number
  wrongCount: number
  lastWrongAt: string
}

// ===== Daily Tasks =====
export interface DailyTask {
  id: number
  title: string
  description: string
  type: 'video' | 'quiz' | 'script'
  targetId: number
  completed: boolean
  reward: number
  deadline: string
}

// ===== Leaderboard =====
export interface LeaderboardEntry {
  userId: number
  name: string
  avatar: string
  storeName: string
  score: number
  rank: number
}

// ===== API Response =====
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}
