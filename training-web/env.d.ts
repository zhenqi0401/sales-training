/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'pinia-plugin-persistedstate' {
  import type { Plugin } from 'pinia'
  const plugin: Plugin
  export default plugin
}
