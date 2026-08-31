import { client } from '../client'
import type { Customization } from './types'

export const customizationApi = {
  async get(enterpriseProductId: string): Promise<Customization> {
    const { data } = await client.get(`/tenant/mdm/customizations/${enterpriseProductId}`)
    return data
  },

  async create(payload: {
    enterprise_product_id: string
    enterprise_sku_id?: string
    sales_price?: number
    purchase_price?: number
    inventory_strategy?: string
    safety_stock?: number
    cost_model?: string
    custom_attributes?: Record<string, unknown>
  }): Promise<Customization> {
    const { data } = await client.post('/tenant/mdm/customizations', payload)
    return data
  },
}