import { client } from '../client'
import type { GroupProduct, GroupSku, GroupCategory, GroupBrand, GroupUnit } from './types'

export const groupProductApi = {
  async list(limit = 50, offset = 0): Promise<GroupProduct[]> {
    const { data } = await client.get('/group/products', { params: { limit, offset } })
    return data
  },

  async get(id: string): Promise<GroupProduct> {
    const { data } = await client.get(`/group/products/${id}`)
    return data
  },

  async create(payload: {
    group_product_code: string
    group_product_name: string
    base_unit_id: string
    group_category_id?: string
    group_brand_id?: string
    spec_template_id?: string
    description?: string
  }): Promise<GroupProduct> {
    const { data } = await client.post('/group/products', payload)
    return data
  },

  async disable(id: string): Promise<void> {
    await client.post(`/group/products/${id}:disable`)
  },

  async listSkus(productId: string): Promise<GroupSku[]> {
    const { data } = await client.get(`/group/products/${productId}/skus`)
    return data
  },

  async addSku(productId: string, payload: {
    group_sku_code: string
    group_sku_name: string
    unit_id: string
    specification_instance?: Record<string, unknown>
    barcode_list?: string[]
    weight?: number
    volume?: number
  }): Promise<GroupSku> {
    const { data } = await client.post(`/group/products/${productId}/skus`, payload)
    return data
  },

  async listCategories(): Promise<GroupCategory[]> {
    const { data } = await client.get('/group/categories')
    return data
  },

  async listBrands(): Promise<GroupBrand[]> {
    const { data } = await client.get('/group/brands')
    return data
  },

  async listUnits(): Promise<GroupUnit[]> {
    const { data } = await client.get('/group/units')
    return data
  },

  async createBrand(payload: { group_brand_code: string; group_brand_name: string }): Promise<GroupBrand> {
    const { data } = await client.post('/group/brands', payload)
    return data
  },

  async createUnit(payload: { group_unit_code: string; group_unit_name: string; is_base_unit?: number }): Promise<GroupUnit> {
    const { data } = await client.post('/group/units', payload)
    return data
  },
}