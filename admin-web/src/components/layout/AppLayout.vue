<template>
  <div class="app-layout" :class="{ collapsed: appStore.sidebarCollapsed }">
    <Sidebar />
    <div class="layout-main">
      <Header />
      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const appStore = useAppStore()
</script>

<style scoped lang="scss">
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;

  .layout-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    margin-left: var(--sidebar-width);
    transition: margin-left 0.3s;
    overflow: hidden;
  }

  &.collapsed {
    .layout-main {
      margin-left: var(--sidebar-collapsed-width);
    }
  }
}

.main-content {
  flex: 1;
  overflow-y: auto;
  background-color: var(--bg-color);
  padding: 0;
}

@media screen and (max-width: 768px) {
  .app-layout {
    .layout-main {
      margin-left: 0;
    }
  }
}
</style>
