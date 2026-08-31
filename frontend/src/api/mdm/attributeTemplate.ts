import { client } from '../client'
import type { AttributeTemplate } from './types'

export const attributeTemplateApi = {
  async listGroup(): Promise<AttributeTemplate[]> {
    const { data } = await client.get('/group/attribute-templates')
    return data
  },

  async listEnterprise(): Promise<AttributeTemplate[]> {
    const { data } = await client.get('/tenant/mdm/attribute-templates')
    return data
  },

  async get(id: string): Promise<AttributeTemplate> {
    const { data } = await client.get(`/group/attribute-templates/${id}`)
    return data
  },

  async create(payload: {
    template_code: string
    template_name: string
    template_level: string
    tenant_id?: string
    attribute_type: string
    is_required?: boolean
    enum_values?: string[]
    min_value?: number
    max_value?: number
  }): Promise<AttributeTemplate> {
    const { data } = await client.post('/group/attribute-templates', payload)
    return data
  },
}