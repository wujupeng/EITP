import { client } from '../client'
import type { NegativePolicyConfig, NegativePolicyAudit } from './types'

export const negativePolicyApi = {
  async get(): Promise<NegativePolicyConfig> {
    const { data } = await client.get('/tenant/mdm/config/negative-inventory-policy')
    return data
  },

  async change(payload: { policy_mode: string; reason: string }): Promise<NegativePolicyAudit> {
    const { data } = await client.put('/tenant/mdm/config/negative-inventory-policy', payload)
    return data
  },

  async listAudit(limit = 50, offset = 0): Promise<NegativePolicyAudit[]> {
    const { data } = await client.get('/tenant/mdm/audit/negative-inventory-policy', { params: { limit, offset } })
    return data
  },
}