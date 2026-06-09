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
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

function getToken(): string | null {
  try {
    const raw = localStorage.getItem('auth-store')
    if (!raw) return null
    return JSON.parse(raw).token || null
  } catch {
    return null
  }
}

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || ''} - 销售培训系统`

  if (to.meta.noAuth) {
    next()
    return
  }

  const token = getToken()
  if (!token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  next()
})

export default router
