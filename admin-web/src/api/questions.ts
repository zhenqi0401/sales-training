import { get, post, put, del } from './index'
import type { Question, QuestionOption, AiGenerateParams, PageResult, Difficulty } from '@/types'

type BackendPage<T> = PageResult<T> & { items?: T[] }
type MessageResponse = { message: string; detail?: string }

function toDifficultyLabel(value: unknown): Difficulty {
  if (value === 'easy' || value === 'medium' || value === 'hard') return value

  const level = Number(value)
  if (level <= 2) return 'easy'
  if (level === 3) return 'medium'
  return 'hard'
}

function toDifficultyValue(value: unknown): number | undefined {
  if (value === undefined || value === null || value === '') return undefined
  if (typeof value === 'number') return value
  if (value === 'easy') return 1
  if (value === 'medium') return 3
  if (value === 'hard') return 5

  const parsed = Number(value)
  return Number.isNaN(parsed) ? undefined : parsed
}

function toDifficultyLevelValue(value: unknown): number | undefined {
  if (value === 'L1') return 1
  if (value === 'L2') return 3
  if (value === 'L3') return 5
  return toDifficultyValue(value)
}

function toOptionList(options: unknown): QuestionOption[] {
  if (Array.isArray(options)) return options as QuestionOption[]
  if (!options || typeof options !== 'object') return []

  return Object.entries(options as Record<string, string>).map(([label, value]) => ({
    label,
    value,
  }))
}

function toOptionMap(options: unknown): Record<string, string> | undefined {
  if (!options) return undefined
  if (!Array.isArray(options)) return options as Record<string, string>

  return options.reduce<Record<string, string>>((result, option) => {
    if (option?.label) result[option.label] = option.value ?? ''
    return result
  }, {})
}

function normalizeQuestion(data: any): Question {
  const type = data.type ?? 'single'
  const rawAnswer = data.answer ?? ''

  return {
    ...data,
    type,
    categoryId: data.categoryId ?? data.category_id,
    videoId: data.videoId ?? data.video_id,
    categoryName: data.categoryName ?? data.category_name,
    difficulty: toDifficultyLabel(data.difficulty),
    options: toOptionList(data.options),
    answer: type === 'multiple' && typeof rawAnswer === 'string'
      ? rawAnswer.split(',').map((item) => item.trim()).filter(Boolean)
      : rawAnswer,
    explanation: data.explanation ?? data.analysis ?? '',
    tags: Array.isArray(data.tags) ? data.tags : [],
    source: data.source ?? '',
    status: data.status ?? (data.is_active === false ? 'disabled' : 'active'),
    createdAt: data.createdAt ?? data.created_at ?? '',
  }
}

function normalizeQuestionPage(data: BackendPage<any>): PageResult<Question> {
  return {
    ...data,
    list: (data.list ?? data.items ?? []).map(normalizeQuestion),
  }
}

function normalizeQuestionParams(params: Record<string, any>): Record<string, any> {
  return {
    ...params,
  }
}

function toQuestionPayload(params: Partial<Question>): Record<string, any> {
  return {
    content: params.content,
    type: params.type,
    options: toOptionMap(params.options),
    answer: Array.isArray(params.answer) ? params.answer.join(',') : params.answer,
    analysis: params.explanation,
    difficulty: toDifficultyLevelValue((params as any).difficultyLevel ?? params.difficulty),
    category_id: params.categoryId,
    video_id: params.videoId,
    tags: params.tags,
  }
}

export function getQuestionList(params: {
  page: number
  pageSize: number
  categoryId?: number
  type?: string
  difficulty?: string
  keyword?: string
  tag?: string
}): Promise<PageResult<Question>> {
  return get<BackendPage<any>>('/questions/', normalizeQuestionParams(params)).then(normalizeQuestionPage)
}

export function getQuestionDetail(id: number): Promise<Question> {
  return get<any>(`/questions/${id}`).then(normalizeQuestion)
}

export function createQuestion(params: Partial<Question>): Promise<Question> {
  return post<any>('/questions/', toQuestionPayload(params)).then(normalizeQuestion)
}

export function updateQuestion(id: number, params: Partial<Question>): Promise<Question> {
  return put<any>(`/questions/${id}`, toQuestionPayload(params)).then(normalizeQuestion)
}

export function deleteQuestion(id: number): Promise<void> {
  return del<void>(`/questions/${id}`)
}

export function aiGenerateQuestions(params: AiGenerateParams): Promise<Question[]> {
  if (!params.videoId) {
    return Promise.reject(new Error('请选择视频'))
  }
  return post<any[]>('/questions/ai-generate', {
    video_id: params.videoId,
    user_requirements: params.userRequirements || '',
    count: params.count,
    difficulty_level: params.difficultyLevel,
    question_type_ratios: params.questionTypeRatios,
    category_id: params.categoryId,
    product_category_id: params.productCategoryId,
    knowledge_points: params.knowledgePoints ?? [],
  }).then((items) => items.map(normalizeQuestion))
}

export function saveReviewedAiQuestions(questions: Partial<Question>[]): Promise<Question[]> {
  return post<any[]>('/questions/ai-review-save', {
    questions: questions.map((question) => ({
      ...toQuestionPayload(question),
      source: 'ai',
    })),
  }).then((items) => items.map(normalizeQuestion))
}

export function batchDeleteQuestions(ids: number[]): Promise<void> {
  return post<void>('/questions/batch-delete', { ids })
}

export function importQuestions(questions: Partial<Question>[]): Promise<MessageResponse> {
  return post<MessageResponse>('/questions/import', {
    questions: questions.map((question) => ({
      ...toQuestionPayload(question),
      source: 'import',
    })),
  })
}
