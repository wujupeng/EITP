import { client } from '../client'
import type { SpecTemplate, AttributeDefinition } from './types'

export const specTemplateApi = {
  async listGroup(): Promise<SpecTemplate[]> {
    const { data } = await client.get('/group/spec-templates')
    return data
  },

  async listEnterprise(): Promise<SpecTemplate[]> {
    const { data } = await client.get('/tenant/mdm/spec-templates')
    return data
  },

  async get(id: string): Promise<SpecTemplate> {
    const { data } = await client.get(`/group/spec-templates/${id}`)
    return data
  },

  async create(payload: {
    template_code: string
    template_name: string
    template_level: string
    tenant_id?: string
    attribute_definitions: AttributeDefinition[]
  }): Promise<SpecTemplate> {
    const { data } = await client.post('/group/spec-templates', payload)
    return data
  },
}