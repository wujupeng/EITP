import { client } from '../client'
import type { MasterDataAudit } from './types'

export const masterDataAuditApi = {
  async list(params: {
    entity_type?: string
    entity_id?: string
    action?: string
    limit?: number
    offset?: number
  }): Promise<MasterDataAudit[]> {
    const { data } = await client.get('/tenant/mdm/audit/master-data', { params })
    return data
  },
}