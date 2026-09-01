import { client } from './client'

export const secApi = {
  executeCertification: (data: { matrix_version?: string; scope?: string; layers?: string[]; modules?: string[]; trigger_source?: string }) =>
    client.post('/sec/certification/execute', data),

  getBatchProgress: (batchId: string) =>
    client.get(`/sec/certification/batches/${batchId}`),

  listReports: (params?: { batch_id?: string; conclusion?: string; format?: string; limit?: number }) =>
    client.get('/sec/reports', { params }),

  getReport: (reportId: string, format?: string) =>
    client.get(`/sec/reports/${reportId}`, { params: { format } }),

  getEvidence: (reportId: string, itemId: string) =>
    client.get(`/sec/reports/${reportId}/items/${itemId}/evidence`),

  issueCertificate: (data: { batch_id: string; issuer: string; signer: string }) =>
    client.post('/sec/certificate/issue', data),

  getCurrentCertificate: () =>
    client.get('/sec/certificate/current'),

  getCertificate: (certId: string) =>
    client.get(`/sec/certificate/${certId}`),

  revokeCertificate: (certId: string, reason: string) =>
    client.post(`/sec/certificate/${certId}/revoke`, { reason }),

  verifyCertificate: (certId: string) =>
    client.get(`/sec/certificate/${certId}/verify`),

  getConfig: () =>
    client.get('/sec/config'),

  updateConfig: (data: { strict_mode?: boolean; alert_channels?: string[]; report_retention_days?: number }) =>
    client.put('/sec/config', data),

  skipItem: (itemId: string, reason: string) =>
    client.put(`/sec/config/items/${itemId}/skip`, { reason }),

  listAudit: (params?: { batch_id?: string; action_type?: string; limit?: number; offset?: number }) =>
    client.get('/sec/audit', { params }),

  submitAccessRequest: (data: { target_tenant_id: string; target_data_scope: string; reason: string }) =>
    client.post('/sec/platform-admin-access/requests', data),

  listAccessRequests: (status?: string) =>
    client.get('/sec/platform-admin-access/requests', { params: { status } }),

  approveAccessRequest: (requestId: string) =>
    client.post(`/sec/platform-admin-access/requests/${requestId}/approve`),

  rejectAccessRequest: (requestId: string, reason: string) =>
    client.post(`/sec/platform-admin-access/requests/${requestId}/reject`, { reason }),

  scanRedisKeys: () =>
    client.post('/sec/redis-key-scan'),

  testJoinLeakage: () =>
    client.post('/sec/join-leakage/test'),

  executeAttackChain: () =>
    client.post('/sec/attack-chain/execute'),
}