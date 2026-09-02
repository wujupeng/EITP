import { client } from './client'

export const prodApi = {
  verification: {
    execute: (data: any) => client.post('/prod/verifications/execute', data),
    executeBatch: (data: any) => client.post('/prod/verifications/execute-batch', data),
    get: (runId: string) => client.get(`/prod/verifications/${runId}`),
    list: (params?: any) => client.get('/prod/verifications', { params }),
    retry: (runId: string) => client.post(`/prod/verifications/${runId}/retry`),
    cancel: (runId: string) => client.delete(`/prod/verifications/${runId}`),
  },
  evidence: {
    get: (evidenceId: string) => client.get(`/prod/evidence/${evidenceId}`),
    list: (params?: any) => client.get('/prod/evidence', { params }),
    download: (evidenceId: string) => client.get(`/prod/evidence/${evidenceId}/download`),
    verifyHash: (data: { evidence_id: string; stored_hash: string; content_ref: string }) =>
      client.post('/prod/evidence/verify-hash', data),
  },
  dossier: {
    assemble: (data: any) => client.post('/prod/dossiers/assemble', data),
    get: (dossierId: string) => client.get(`/prod/dossiers/${dossierId}`),
    list: (params?: any) => client.get('/prod/dossiers', { params }),
    sign: (dossierId: string, data: any) => client.post(`/prod/dossiers/${dossierId}/sign`, data),
    export: (dossierId: string) => client.get(`/prod/dossiers/${dossierId}/export`),
  },
  coreFreeze: {
    fingerprints: () => client.get('/prod/core-freeze/fingerprints'),
    verify: () => client.post('/prod/core-freeze/verify'),
  },
}