import { client } from '../client'
import type { GovernanceRequest } from './types'

export const governanceApi = {
  async listGroup(limit = 50, offset = 0): Promise<GovernanceRequest[]> {
    const { data } = await client.get('/group/governance-requests', { params: { limit, offset } })
    return data
  },

  async createGroup(payload: {
    entity_type: string
    entity_id: string
    governance_level: string
    tenant_id?: string
  }): Promise<GovernanceRequest> {
    const { data } = await client.post('/group/governance-requests', payload)
    return data
  },

  async submit(requestId: string): Promise<{ workflow_id: string; state: string }> {
    const { data } = await client.post(`/group/governance-requests/${requestId}:submit`)
    return data
  },

  async approve(requestId: string, reason: string): Promise<{ workflow_id: string; state: string }> {
    const { data } = await client.post(`/group/governance-requests/${requestId}:approve`, { reason })
    return data
  },

  async reject(requestId: string, reason: string): Promise<{ workflow_id: string; state: string }> {
    const { data } = await client.post(`/group/governance-requests/${requestId}:reject`, { reason })
    return data
  },

  async publish(requestId: string): Promise<{ workflow_id: string; state: string }> {
    const { data } = await client.post(`/group/governance-requests/${requestId}:publish`)
    return data
  },

  async rollback(requestId: string, reason: string): Promise<{ workflow_id: string; state: string }> {
    const { data } = await client.post(`/group/governance-requests/${requestId}:rollback`, { reason })
    return data
  },

  async listEnterprise(limit = 50, offset = 0): Promise<GovernanceRequest[]> {
    const { data } = await client.get('/tenant/mdm/governance-requests', { params: { limit, offset } })
    return data
  },

  async createEnterprise(payload: {
    entity_type: string
    entity_id: string
    governance_level: string
  }): Promise<GovernanceRequest> {
    const { data } = await client.post('/tenant/mdm/governance-requests', payload)
    return data
  },
}