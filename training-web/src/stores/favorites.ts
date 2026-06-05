import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SalesScript } from '@/types'

export const useFavoritesStore = defineStore(
  'favorites',
  () => {
    // State
    const favoriteScriptIds = ref<number[]>([])
    const favoriteScripts = ref<SalesScript[]>([])

    // Getters
    const isFavorite = computed(() => (id: number) => favoriteScriptIds.value.includes(id))
    const favoriteCount = computed(() => favoriteScriptIds.value.length)

    // Actions
    function toggleFavorite(script: SalesScript) {
      const index = favoriteScriptIds.value.indexOf(script.id)
      if (index !== -1) {
        favoriteScriptIds.value.splice(index, 1)
        const sIndex = favoriteScripts.value.findIndex((s) => s.id === script.id)
        if (sIndex !== -1) favoriteScripts.value.splice(sIndex, 1)
      } else {
        favoriteScriptIds.value.push(script.id)
        favoriteScripts.value.push(script)
        script.isFavorite = true
      }
    }

    function setFavorites(scripts: SalesScript[]) {
      favoriteScripts.value = scripts
      favoriteScriptIds.value = scripts.map((s) => s.id)
    }

    function removeFavorite(scriptId: number) {
      const index = favoriteScriptIds.value.indexOf(scriptId)
      if (index !== -1) {
        favoriteScriptIds.value.splice(index, 1)
        const sIndex = favoriteScripts.value.findIndex((s) => s.id === scriptId)
        if (sIndex !== -1) favoriteScripts.value.splice(sIndex, 1)
      }
    }

    function clearFavorites() {
      favoriteScriptIds.value = []
      favoriteScripts.value = []
    }

    return {
      favoriteScriptIds,
      favoriteScripts,
      isFavorite,
      favoriteCount,
      toggleFavorite,
      setFavorites,
      removeFavorite,
      clearFavorites
    }
  },
  {
    persist: {
      key: 'favorites-store',
      storage: localStorage
    }
  }
)
