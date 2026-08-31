import { client } from '../client'
import type { ProductReference } from './types'

export const referenceApi = {
  async list(): Promise<ProductReference[]> {
    const { data } = await client.get('/tenant/mdm/product-references')
    return data
  },

  async listByGroupProduct(groupProductId: string): Promise<ProductReference[]> {
    const { data } = await client.get(`/group/products/${groupProductId}/references`)
    return data
  },
}