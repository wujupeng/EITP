import { client } from '../client'
import type { EnterpriseProduct } from './types'

export const enterpriseProductApi = {
  async list(limit = 50, offset = 0): Promise<EnterpriseProduct[]> {
    const { data } = await client.get('/tenant/mdm/enterprise-products', { params: { limit, offset } })
    return data
  },

  async get(id: string): Promise<EnterpriseProduct> {
    const { data } = await client.get(`/tenant/mdm/enterprise-products/${id}`)
    return data
  },

  async reference(payload: {
    group_product_id: string
    enterprise_product_code: string
    enterprise_product_name?: string
    enterprise_category_id?: string
  }): Promise<EnterpriseProduct> {
    const { data } = await client.post('/tenant/mdm/enterprise-products:reference', payload)
    return data
  },

  async releaseReference(id: string): Promise<void> {
    await client.post(`/tenant/mdm/enterprise-products/${id}:release-reference`)
  },
}