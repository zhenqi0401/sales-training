import type { UserInfo } from '@/types'

type RawTrainingUser = {
  id?: number | null
  name?: string | null
  phone?: string | null
  avatar?: string | null
  storeName?: string | null
  joinDate?: string | null
  level?: number | null
  point?: number | null
  mustChangePassword?: boolean | null
  username?: string | null
  real_name?: string | null
  realName?: string | null
  store_name?: string | null
  created_at?: string | null
  createdAt?: string | null
  must_change_password?: boolean | null
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

export function normalizeTrainingUser(raw: RawTrainingUser): UserInfo {
  const name = text(raw.name) || text(raw.real_name) || text(raw.realName) || text(raw.username)

  return {
    id: numberValue(raw.id, 0),
    name,
    phone: text(raw.phone),
    avatar: text(raw.avatar),
    storeName: text(raw.storeName) || text(raw.store_name),
    joinDate: text(raw.joinDate) || text(raw.created_at) || text(raw.createdAt),
    level: numberValue(raw.level, 1),
    point: numberValue(raw.point, 0),
    mustChangePassword: raw.mustChangePassword === true || raw.must_change_password === true,
  }
}

export function shouldRefreshCachedUser(
  token: string,
  user: UserInfo | null,
  hasFetchedUserInfo: boolean,
): boolean {
  return Boolean(token) && (!user || !hasFetchedUserInfo)
}
