<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const active = ref(0)

const tabs = [
  { name: 'Home', label: '首页', icon: 'home-o', path: '/home' },
  { name: 'Courses', label: '课程', icon: 'shopping-cart-o', path: '/courses' },
  { name: 'Practice', label: '演练', icon: 'fire-o', path: '/practice' },
  { name: 'Exam', label: '考试', icon: 'records-o', path: '/exam' },
  { name: 'Profile', label: '我的', icon: 'contact-o', path: '/profile' }
]

const currentIndex = computed(() => {
  const idx = tabs.findIndex((t) => route.path.startsWith(t.path))
  return idx !== -1 ? idx : 0
})

watch(currentIndex, (val) => {
  active.value = val
}, { immediate: true })

function onTabChange(index: number) {
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  router.push(tabs[index].path)
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
