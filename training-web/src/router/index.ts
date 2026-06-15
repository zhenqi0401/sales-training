import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/init-password',
    name: 'InitPassword',
    component: () => import('@/views/login/init-password.vue'),
    meta: { requiresAuth: true, allowChangePassword: true }
  },
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/home/index.vue'),
    meta: { requiresAuth: true, keepAlive: true, showTabBar: true }
  },
  {
    path: '/courses',
    name: 'Courses',
    component: () => import('@/views/courses/index.vue'),
    meta: { requiresAuth: true, keepAlive: true, showTabBar: true }
  },
  {
    path: '/courses/list/:categoryId',
    name: 'CourseList',
    component: () => import('@/views/courses/list.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/courses/play/:videoId',
    name: 'CoursePlay',
    component: () => import('@/views/courses/play.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/courses/scripts',
    name: 'CourseScripts',
    component: () => import('@/views/courses/scripts.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/courses/script/:scriptId',
    name: 'CourseScriptDetail',
    component: () => import('@/views/courses/script-detail.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/practice',
    name: 'Practice',
    component: () => import('@/views/practice/index.vue'),
    meta: { requiresAuth: true, keepAlive: true, showTabBar: true }
  },
  {
    path: '/practice/module/:moduleId',
    name: 'PracticeModule',
    component: () => import('@/views/practice/module.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/practice/agent/:moduleCode?',
    name: 'PracticeAgent',
    component: () => import('@/views/practice/agent.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/scripts',
    name: 'Scripts',
    component: () => import('@/views/scripts/index.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/scripts/:id',
    name: 'ScriptDetail',
    component: () => import('@/views/scripts/detail.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('@/views/products/index.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/products/:id',
    name: 'ProductDetail',
    component: () => import('@/views/products/detail.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/exam',
    name: 'Exam',
    component: () => import('@/views/exam/index.vue'),
    meta: { requiresAuth: true, keepAlive: true, showTabBar: true }
  },
  {
    path: '/exam/taking/:level',
    name: 'ExamTaking',
    component: () => import('@/views/exam/taking.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/exam/result/:recordId',
    name: 'ExamResult',
    component: () => import('@/views/exam/result.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/exam/wrong-book',
    name: 'WrongBook',
    component: () => import('@/views/exam/wrong-book.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/profile/index.vue'),
    meta: { requiresAuth: true, keepAlive: true, showTabBar: true }
  },
  {
    path: '/profile/records',
    name: 'LearningRecords',
    component: () => import('@/views/profile/records.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: false }
  },
  {
    path: '/sales/dashboard',
    name: 'SalesDashboard',
    component: () => import('@/views/sales/dashboard.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: true, requiresSales: true }
  },
  {
    path: '/sales/methodology',
    name: 'SalesMethodology',
    component: () => import('@/views/sales/methodology.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: true, requiresSales: true }
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// Auth guard
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth !== false && authStore.needsUserInfoRefresh()) {
    await authStore.fetchUserInfo()
  }

  if (to.meta.requiresAuth !== false && !authStore.isLoggedIn) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (authStore.mustChangePassword && !to.meta.allowChangePassword) {
    next({ path: '/init-password' })
  } else if (to.path === '/init-password' && authStore.isLoggedIn && !authStore.mustChangePassword) {
    next({ path: '/home' })
  } else if (to.path === '/login' && authStore.isLoggedIn) {
    next({ path: '/home' })
  } else if (
    to.meta.requiresAuth !== false &&
    authStore.isLoggedIn &&
    authStore.userRole !== '' &&
    !['sales', 'student'].includes(authStore.userRole)
  ) {
    authStore.logout()
    next({ path: '/login' })
  } else if (to.meta.requiresSales && authStore.userRole !== 'sales') {
    next({ path: '/home' })
  } else {
    next()
  }
})

export default router
