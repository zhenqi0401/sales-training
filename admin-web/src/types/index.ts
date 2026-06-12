// ==================== User Types ====================
export interface UserInfo {
  id: number
  username: string
  realName: string
  avatar?: string
  email?: string
  phone?: string
  role: 'admin' | 'sales' | 'student'
  storeId?: number
  storeName?: string
  status: 0 | 1
  createdAt: string
  _statusLoading?: boolean
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
  categoryId: number | null
  categoryName?: string
  url: string
  coverUrl?: string
  tags: string[]
  productIds: number[]
  productNames?: string[]
  duration: number
  resolution?: string
  fileSize: number
  status: 'draft' | 'published' | 'archived'
  viewCount: number
  required: boolean
  sortOrder: number
  estDuration: number
  createdAt: string
  updatedAt: string
}

export interface VideoUploadParams {
  title: string
  description?: string
  categoryId: number
  url: string
  coverUrl?: string
  tags?: string[]
  productIds?: number[]
  duration?: number
  resolution?: string
  fileSize?: number
  status?: 'draft' | 'published' | 'archived'
  sortOrder?: number
  required?: boolean
  estDuration?: number
}

// ==================== Question Types ====================
export type QuestionType = 'single' | 'multiple' | 'true_false' | 'fill_blank' | 'essay'
export type Difficulty = 'easy' | 'medium' | 'hard'

export interface Question {
  id: number
  type: QuestionType
  difficulty: Difficulty
  categoryId: number | null
  videoId?: number | null
  categoryName?: string
  content: string
  options: QuestionOption[]
  answer: string | string[]
  explanation?: string
  tags: string[]
  source?: string
  status: 'active' | 'disabled'
  createdAt: string
}

export interface QuestionOption {
  label: string
  value: string
}

export interface AiGenerateParams {
  videoId: number | null
  categoryId?: number | null
  productCategoryId?: number | null
  count: number
  difficultyLevel: 'L1' | 'L2' | 'L3'
  questionTypeRatios: {
    single: number
    multiple: number
    true_false: number
  }
  knowledgePoints?: string[]
  userRequirements?: string
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
  totalExams?: number
  averageScore?: number
}

export interface DashboardOverview {
  totalUsers: number
  activeUsers: number
  totalVideos: number
  totalQuestions: number
  totalStores: number
  totalExams: number
  completionRate: number
  totalWatchMinutes: number
  averageLearningMinutes: number
  examPassRate: number
  averageScore: number
  examPassRateByLevel: Record<string, number>
}

export interface DashboardVideoStat {
  videoId: number
  title: string
  categoryName: string
  durationMinutes: number
  watchers: number
  completionRate: number
  averageWatchMinutes: number
  totalWatchMinutes: number
  rankScore: number
}

export interface DashboardStudentStat {
  userId: number
  name: string
  phone: string
  storeId?: number | null
  storeName: string
  watchMinutes: number
  completedVideos: number
  totalVideos: number
  completionRate: number
  averageProgress: number
  examCount: number
  examPassed: number
  examPassRate: number
  averageScore: number
  bestScore: number
}

export interface DashboardStoreStat {
  storeId?: number | null
  storeName: string
  studentCount: number
  completionRate: number
  averageWatchMinutes: number
  examPassRate: number
  averageScore: number
}

export interface DashboardExamLevelStat {
  level: string
  count: number
  averageScore: number
  passRate: number
}

export interface DashboardPaperStat {
  paperId: number
  paperTitle: string
  level: string
  count: number
  averageScore: number
  passRate: number
}

export interface DashboardWrongQuestionStat {
  questionId: number
  content: string
  categoryName: string
  wrongCount: number
}

export interface DashboardWeakKnowledgeStat {
  name: string
  wrongCount: number
}

export interface DashboardTrendStat {
  date: string
  count: number
  averageScore: number
  passRate: number
}

export interface DashboardData {
  total_users?: number
  active_users?: number
  total_videos?: number
  total_questions?: number
  total_stores?: number
  total_exams?: number
  exam_pass_rate?: number
  completion_rate?: number
  average_score?: number
  overview: DashboardOverview
  videoStats: {
    items: DashboardVideoStat[]
    ranking: DashboardVideoStat[]
  }
  studentStats: {
    progressList: DashboardStudentStat[]
    learningRanking: DashboardStudentStat[]
    examRanking: DashboardStudentStat[]
  }
  storeStats: DashboardStoreStat[]
  examStats: {
    levels: DashboardExamLevelStat[]
    papers: DashboardPaperStat[]
    highFrequencyWrong: DashboardWrongQuestionStat[]
    weakKnowledge: DashboardWeakKnowledgeStat[]
    trend: DashboardTrendStat[]
  }
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
