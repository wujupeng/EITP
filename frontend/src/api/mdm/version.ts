import { client } from '../client'
import type { MasterDataVersion, VersionCompareResult } from './types'

export const versionApi = {
  async listGroup(entityType: string, entityId: string): Promise<MasterDataVersion[]> {
    const { data } = await client.get('/group/versions', { params: { entity_type: entityType, entity_id: entityId } })
    return data
  },

  async listEnterprise(entityType: string, entityId: string): Promise<MasterDataVersion[]> {
    const { data } = await client.get('/tenant/mdm/versions', { params: { entity_type: entityType, entity_id: entityId } })
    return data
  },

  async compare(payload: {
    entity_type: string
    entity_id: string
    version_a: number
    version_b: number
  }): Promise<VersionCompareResult> {
    const { data } = await client.post('/group/versions:compare', payload)
    return data
  },

  async getVersion(entityType: string, entityId: string, versionNumber: number): Promise<MasterDataVersion> {
    const { data } = await client.get(`/group/versions/${entityType}/${entityId}/${versionNumber}`)
    return data
  },
}