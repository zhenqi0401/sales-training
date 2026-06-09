<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import TabBar from '@/components/layout/TabBar.vue'
import NavBar from '@/components/layout/NavBar.vue'

const route = useRoute()

const showTabBar = computed(() => route.meta?.showTabBar === true)
const showNavBar = computed(() => route.meta?.showTabBar !== true && route.name !== 'Login' && route.name !== 'InitPassword')

// Dynamic page title based on route
const pageTitle = computed(() => {
  const name = route.name as string
  const titleMap: Record<string, string> = {
    Scripts: '话术',
    Products: '产品知识',
    CourseList: '课程列表',
    CoursePlay: '视频学习',
    PracticeModule: '演练模块',
    ScriptDetail: '话术详情',
    ProductDetail: '产品详情',
    ExamTaking: '考试中',
    ExamResult: '考试结果',
    WrongBook: '错题本',
    LearningRecords: '学习记录'
  }
  return titleMap[name] ?? ''
})
</script>

<template>
  <ConfigProvider>
    <div class="app-container">
      <NavBar v-if="showNavBar" :title="pageTitle" />
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <keep-alive :include="['Home', 'Courses', 'Practice', 'Scripts', 'Products', 'Exam', 'Profile']">
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
      <TabBar v-if="showTabBar" />
    </div>
  </ConfigProvider>
</template>

<style lang="scss">
.app-container {
  width: 100%;
  min-height: 100vh;
  background: $bg;
}
</style>
