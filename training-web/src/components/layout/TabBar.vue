<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { computed, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const pendingActive = ref<number | null>(null)

const tabs = [
  { name: 'Home', label: '首页', icon: 'home-o', path: '/home' },
  { name: 'Courses', label: '课程', icon: 'shopping-cart-o', path: '/courses' },
  { name: 'Practice', label: '演练', icon: 'fire-o', path: '/practice' },
  { name: 'Exam', label: '考试', icon: 'records-o', path: '/exam' },
  { name: 'Profile', label: '我的', icon: 'contact-o', path: '/profile' }
]

const routeActive = computed(() => {
  const idx = tabs.findIndex((t) => route.path.startsWith(t.path))
  return idx !== -1 ? idx : 0
})

const active = computed({
  get: () => pendingActive.value ?? routeActive.value,
  set: (value) => {
    pendingActive.value = Number(value)
  }
})

watch(
  () => route.fullPath,
  () => {
    pendingActive.value = null
  }
)

async function onTabChange(index: number | string) {
  const nextIndex = Number(index)
  const tab = tabs[nextIndex]
  if (!tab) {
    pendingActive.value = null
    return
  }

  pendingActive.value = nextIndex

  if (!authStore.isLoggedIn) {
    await router.push('/login')
    return
  }

  if (route.path === tab.path) {
    pendingActive.value = null
    return
  }

  try {
    await router.push(tab.path)
  } catch {
    pendingActive.value = null
  }
}
</script>

<template>
  <van-tabbar
    v-model="active"
    :border="true"
    active-color="var(--primary)"
    inactive-color="var(--text-muted)"
    @change="onTabChange"
    safe-area-inset-bottom
  >
    <van-tabbar-item
      v-for="(tab, index) in tabs"
      :key="index"
      :icon="tab.icon"
    >
      {{ tab.label }}
    </van-tabbar-item>
  </van-tabbar>
</template>

<style lang="scss" scoped>
.van-tabbar {
  z-index: 100;
}
</style>
