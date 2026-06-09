<template>
  <div class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <div class="logo" @click="router.push('/dashboard')">
      <el-icon :size="28"><Reading /></el-icon>
      <span v-show="!appStore.sidebarCollapsed" class="logo-text">培训管理系统</span>
    </div>

    <el-menu
      :default-active="activeMenu"
      :collapse="appStore.sidebarCollapsed"
      :collapse-transition="false"
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409eff"
      @select="handleSelect"
    >
      <template v-for="item in appStore.menuItems" :key="item.path">
        <el-sub-menu v-if="item.children && item.children.length" :index="item.path || item.title">
          <template #title>
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </template>
          <el-menu-item
            v-for="child in item.children"
            :key="child.path"
            :index="child.path"
          >
            <el-icon><component :is="child.icon" /></el-icon>
            <template #title>{{ child.title }}</template>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item v-else :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </template>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import router from '@/router'

const route = useRoute()
const appStore = useAppStore()

const menuPaths = computed(() => {
  return appStore.menuItems.flatMap((item) => {
    if (item.children?.length) {
      return item.children.map((child) => child.path)
    }

    return item.path ? [item.path] : []
  })
})

const activeMenu = computed(() => {
  if (menuPaths.value.includes(route.fullPath)) {
    return route.fullPath
  }

  const parentPath = menuPaths.value.find((path) => path && route.path.startsWith(path.split('?')[0]))
  return parentPath ?? route.path
})

function handleSelect(index: string) {
  if (index && index !== route.fullPath) {
    router.push(index)
  }
}
</script>

<style scoped lang="scss">
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background-color: var(--sidebar-bg);
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.3s;
  z-index: 1001;
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.1);

  &.collapsed {
    width: var(--sidebar-collapsed-width);

    .logo-text {
      display: none;
    }
  }

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: #fff;
    cursor: pointer;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    .logo-text {
      font-size: 16px;
      font-weight: 600;
      white-space: nowrap;
    }
  }
}

// Scrollbar for sidebar
.sidebar::-webkit-scrollbar {
  width: 4px;
}

.sidebar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

// Mobile overlay
@media screen and (max-width: 768px) {
  .sidebar {
    width: var(--sidebar-collapsed-width);

    .logo-text {
      display: none;
    }

    &:not(.collapsed) {
      width: var(--sidebar-width);
      box-shadow: 2px 0 12px rgba(0, 0, 0, 0.3);

      .logo-text {
        display: inline;
      }
    }
  }
}
</style>
