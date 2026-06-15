import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/index.vue'), meta: { title: '数据看板' } },
      { path: 'categories', name: 'Categories', component: () => import('@/views/categories/index.vue'), meta: { title: '分类管理' } },
      { path: 'videos', name: 'Videos', component: () => import('@/views/videos/index.vue'), meta: { title: '视频管理' } },
      { path: 'videos/edit/:id?', name: 'VideoEdit', component: () => import('@/views/videos/edit.vue'), meta: { title: '视频编辑' } },
      { path: 'questions', name: 'Questions', component: () => import('@/views/questions/index.vue'), meta: { title: '题目管理' } },
      { path: 'questions/edit/:id?', name: 'QuestionEdit', component: () => import('@/views/questions/edit.vue'), meta: { title: '题目编辑' } },
      { path: 'questions/ai-generate', name: 'AiGenerate', component: () => import('@/views/questions/ai-generate.vue'), meta: { title: 'AI出题' } },
      { path: 'exams', name: 'Exams', component: () => import('@/views/exams/index.vue'), meta: { title: '试卷管理' } },
      { path: 'exams/edit/:id?', name: 'ExamEdit', component: () => import('@/views/exams/edit.vue'), meta: { title: '试卷编辑' } },
      { path: 'users', name: 'Users', component: () => import('@/views/users/index.vue'), meta: { title: '用户管理' } },
      { path: 'users/detail/:id', name: 'UserDetail', component: () => import('@/views/users/detail.vue'), meta: { title: '用户详情' } },
      { path: 'scripts', name: 'Scripts', component: () => import('@/views/scripts/index.vue'), meta: { title: '话术管理' } },
      { path: 'products', name: 'Products', component: () => import('@/views/products/index.vue'), meta: { title: '产品知识' } },
      { path: 'stores', name: 'Stores', component: () => import('@/views/stores/index.vue'), meta: { title: '门店管理' } },
      { path: 'sales', name: 'Sales', component: () => import('@/views/sales/index.vue'), meta: { title: '销售管理' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

function getAuthInfo(): { token: string | null; role: string | null } {
  try {
    const raw = localStorage.getItem('auth-store')
    if (!raw) return { token: null, role: null }
    const parsed = JSON.parse(raw)
    return { token: parsed.token || null, role: parsed.role || null }
  } catch {
    return { token: null, role: null }
  }
}

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || ''} - 销售培训系统`

  if (to.meta.noAuth) {
    next()
    return
  }

  const { token, role } = getAuthInfo()
  if (!token) {
    console.warn('[RouterGuard] No token found, redirecting to login. Target:', to.fullPath)
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 管理端只允许 admin（兼容旧角色值 super_admin / training_admin / instructor）
  const ADMIN_ROLES = ['admin', 'super_admin', 'training_admin', 'instructor']
  if (role && !ADMIN_ROLES.includes(role)) {
    console.warn('[RouterGuard] Non-admin role detected:', role, 'redirecting to login.')
    next({ path: '/login', query: { error: 'no_permission' } })
    return
  }

  next()
})

export default router
