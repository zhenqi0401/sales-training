import http from './index'
import type { ApiResponse, ProductCategory, Product } from '@/types'

/**
 * Product Knowledge API
 */
export const productsApi = {
  /**
   * Get product categories
   */
  getCategories() {
    return http.get<ApiResponse<ProductCategory[]>>('/products/categories')
  },

  /**
   * Get products by category
   */
  getProductsByCategory(categoryId: number) {
    return http.get<ApiResponse<Product[]>>(`/products/categories/${categoryId}/products`)
  },

  /**
   * Get product detail
   */
  getProductDetail(productId: number) {
    return http.get<ApiResponse<Product>>(`/products/${productId}`)
  },

  /**
   * Search products
   */
  searchProducts(keyword: string) {
    return http.get<ApiResponse<Product[]>>('/products/search', {
      params: { keyword }
    })
  }
}
