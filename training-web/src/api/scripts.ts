import http from './index'
import type { ApiResponse, ScriptCategory, SalesScript, PaginatedData } from '@/types'

function unwrapResponse<T>(request: Promise<unknown>) {
  return request as Promise<ApiResponse<T>>
}

/**
 * Sales Scripts API
 */
export const scriptsApi = {
  /**
   * Get script categories (by master theory)
   */
  getCategories() {
    return unwrapResponse<ScriptCategory[]>(http.get<ApiResponse<ScriptCategory[]>>('/scripts/categories'))
  },

  /**
   * Get scripts by category
   */
  getScriptsByCategory(categoryId: number) {
    return unwrapResponse<SalesScript[]>(http.get<ApiResponse<SalesScript[]>>(`/scripts/categories/${categoryId}/scripts`))
  },

  /**
   * Get script detail
   */
  getScriptDetail(id: number) {
    return unwrapResponse<SalesScript>(http.get<ApiResponse<SalesScript>>(`/scripts/${id}`))
  },

  /**
   * Search scripts
   */
  searchScripts(keyword: string, page = 1, pageSize = 10) {
    return unwrapResponse<PaginatedData<SalesScript>>(http.get<ApiResponse<PaginatedData<SalesScript>>>('/scripts/search', {
      params: { keyword, page, pageSize }
    }))
  },

  /**
   * Toggle favorite
   */
  toggleFavorite(scriptId: number) {
    return unwrapResponse<{ isFavorite: boolean }>(http.post<ApiResponse<{ isFavorite: boolean }>>(`/scripts/${scriptId}/favorite`))
  },

  /**
   * Get favorite scripts
   */
  getFavorites() {
    return unwrapResponse<SalesScript[]>(http.get<ApiResponse<SalesScript[]>>('/scripts/favorites'))
  }
}
