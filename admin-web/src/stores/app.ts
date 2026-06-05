import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { RouteRecordRaw } from 'vue-router'

interface MenuItem {
  title: string
  icon: string
  path: string
  children?: MenuItem[]
}

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const breadcrumb = ref<{ title: string; path?: string }[]>([])
  const menuItems = ref<MenuItem[]>([
    {
      title: '数据看板',
      icon: 'DataAnalysis',
      path: '/dashboard',
    },
    {
      title: '课程管理',
      icon: 'VideoCamera',
      path: '',
      children: [
        { title: '分类管理', icon: 'Collection', path: '/categories' },
        { title: '视频管理', icon: 'VideoCamera', path: '/videos' },
      ],
    },
    {
      title: '题库管理',
      icon: 'Document',
      path: '',
      children: [
        { title: '题目管理', icon: 'Document', path: '/questions' },
        { title: '试卷管理', icon: 'Reading', path: '/exams' },
        { title: 'AI出题', icon: 'MagicStick', path: '/questions/ai-generate' },
      ],
    },
    {
      title: '用户管理',
      icon: 'User',
      path: '',
      children: [
        { title: '管理员', icon: 'UserFilled', path: '/users?role=admin' },
        { title: '学员管理', icon: 'User', path: '/users?role=student' },
      ],
    },
    {
      title: '内容管理',
      icon: 'Notebook',
      path: '',
      children: [
        { title: '话术管理', icon: 'ChatLineSquare', path: '/scripts' },
        { title: '产品知识', icon: 'Goods', path: '/products' },
      ],
    },
    {
      title: '系统设置',
      icon: 'Setting',
      path: '',
      children: [
        { title: '门店管理', icon: 'Shop', path: '/stores' },
      ],
    },
  ])

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setBreadcrumb(items: { title: string; path?: string }[]) {
    breadcrumb.value = items
  }

  function loadSettings() {
    const saved = localStorage.getItem('sidebar-collapsed')
    if (saved) {
      sidebarCollapsed.value = saved === 'true'
    }
  }

  function saveSettings() {
    localStorage.setItem('sidebar-collapsed', String(sidebarCollapsed.value))
  }

  return {
    sidebarCollapsed,
    breadcrumb,
    menuItems,
    toggleSidebar,
    setBreadcrumb,
    loadSettings,
    saveSettings,
  }
})
