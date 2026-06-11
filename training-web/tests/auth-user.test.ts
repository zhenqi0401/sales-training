import assert from 'node:assert/strict'
import { shouldRefreshCachedUser, normalizeTrainingUser } from '../src/stores/auth-user.ts'

assert.equal(shouldRefreshCachedUser('auth-token', null, false), true)
assert.equal(
  shouldRefreshCachedUser('auth-token', { id: 1, name: '????' }, false),
  true
)
assert.equal(
  shouldRefreshCachedUser('auth-token', { id: 1, name: '测试学员' }, false),
  true
)
assert.equal(
  shouldRefreshCachedUser('auth-token', { id: 1, name: '测试学员' }, true),
  false
)

assert.deepEqual(
  normalizeTrainingUser({
    id: 3,
    username: 'student_3312',
    real_name: '测试学员',
    phone: '18611203312',
    avatar: null,
    store_name: '旗舰店',
    created_at: '2026-06-10T00:00:00Z',
    must_change_password: false
  }),
  {
    id: 3,
    name: '测试学员',
    phone: '18611203312',
    avatar: '',
    storeName: '旗舰店',
    joinDate: '2026-06-10T00:00:00Z',
    level: 1,
    point: 0,
    mustChangePassword: false
  }
)
