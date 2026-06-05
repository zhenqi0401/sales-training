import http from './index'
import type { ApiResponse, ScriptCategory, SalesScript, PaginatedData } from '@/types'

/**
 * Sales Scripts API
 */
export const scriptsApi = {
  /**
   * Get script categories (by master theory)
   */
  getCategories() {
    return http.get<ApiResponse<ScriptCategory[]>>('/scripts/categories')
  },

  /**
   * Get scripts by category
   */
  getScriptsByCategory(categoryId: number) {
    return http.get<ApiResponse<SalesScript[]>>(`/scripts/categories/${categoryId}/scripts`)
  },

  /**
   * Get script detail
   */
  getScriptDetail(id: number) {
    return http.get<ApiResponse<SalesScript>>(`/scripts/${id}`)
  },

  /**
   * Search scripts
   */
  searchScripts(keyword: string, page = 1, pageSize = 10) {
    return http.get<ApiResponse<PaginatedData<SalesScript>>>('/scripts/search', {
      params: { keyword, page, pageSize }
    })
  },

  /**
   * Toggle favorite
   */
  toggleFavorite(scriptId: number) {
    return http.post<ApiResponse<{ isFavorite: boolean }>>(`/scripts/${scriptId}/favorite`)
  },

  /**
   * Get favorite scripts
   */
  getFavorites() {
    return http.get<ApiResponse<SalesScript[]>>('/scripts/favorites')
  }
}
