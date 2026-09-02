import { client } from './client'

export const pltApi = {
  audit: {
    records: (params?: any) => client.get('/plt/audit/records', { params }),
    tamperCheck: (data: { tenant_id: string }) => client.post('/plt/audit/tamper-check', data),
    export: (params: any) => client.get('/plt/audit/export', { params }),
    getRetention: (params: { tenant_id: string; module: string }) => client.get('/plt/audit/retention', { params }),
    setRetention: (data: { tenant_id: string; module: string; retention_days: number }) => client.put('/plt/audit/retention', data),
    archive: (data: { tenant_id: string; module?: string }) => client.post('/plt/audit/archive', data),
  },
  consistency: {
    outboxEvents: (params?: any) => client.get('/plt/consistency/outbox/events', { params }),
    retryOutbox: (eventId: string) => client.post(`/plt/consistency/outbox/events/${eventId}/retry`),
    sagaInstances: (params?: any) => client.get('/plt/consistency/saga/instances', { params }),
    sagaDetail: (sagaId: string) => client.get(`/plt/consistency/saga/instances/${sagaId}`),
    compensateSaga: (sagaId: string) => client.post(`/plt/consistency/saga/instances/${sagaId}/compensate`),
  },
  idempotency: {
    records: (params: { tenant_id: string; limit?: number }) => client.get('/plt/idempotency/records', { params }),
    delete: (key: string) => client.delete(`/plt/idempotency/records/${key}`),
  },
  permission: {
    matrix: (params?: any) => client.get('/plt/permission/matrix', { params }),
    createEntry: (data: any) => client.post('/plt/permission/matrix', data),
    approve: (data: { entry_id: string; approver: string; status: string }) => client.post('/plt/permission/matrix/approve', data),
    menu: (params: { tenant_id: string }) => client.get('/plt/permission/menu', { params }),
  },
  tenant: {
    freeze: (data: { tenant_id: string; reason: string }) => client.post('/plt/tenant/freeze', data),
    unfreeze: (data: { tenant_id: string; reason: string }) => client.post('/plt/tenant/unfreeze', data),
    archive: (data: { tenant_id: string; reason: string }) => client.post('/plt/tenant/archive', data),
    quota: (tenantId: string) => client.get(`/plt/tenant/quota/${tenantId}`),
    setQuota: (data: any) => client.put('/plt/tenant/quota', data),
    lifecycle: (tenantId: string) => client.get(`/plt/tenant/lifecycle/${tenantId}`),
  },
  observability: {
    metrics: () => client.get('/plt/observability/metrics', { responseType: 'text' }),
    health: () => client.get('/plt/observability/health'),
    dashboard: () => client.get('/plt/observability/dashboard'),
  },
  config: {
    revisions: (params?: any) => client.get('/plt/config/revisions', { params }),
    createRevision: (data: any) => client.post('/plt/config/revisions', data),
    getRevision: (id: string) => client.get(`/plt/config/revisions/${id}`),
    getValue: (key: string, params?: any) => client.get(`/plt/config/value/${key}`, { params }),
  },
  job: {
    definitions: (params?: any) => client.get('/plt/job/definitions', { params }),
    createDefinition: (data: any) => client.post('/plt/job/definitions', data),
    enable: (jobId: string) => client.post(`/plt/job/definitions/${jobId}/enable`),
    disable: (jobId: string) => client.post(`/plt/job/definitions/${jobId}/disable`),
    execute: (jobId: string) => client.post(`/plt/job/definitions/${jobId}/execute`),
    executions: (params?: any) => client.get('/plt/job/executions', { params }),
  },
  apiGovernance: {
    contracts: (params?: any) => client.get('/plt/api-governance/contracts', { params }),
    createContract: (data: any) => client.post('/plt/api-governance/contracts', data),
    rateLimits: (params?: any) => client.get('/plt/api-governance/rate-limits', { params }),
    createRateLimit: (data: any) => client.post('/plt/api-governance/rate-limits', data),
  },
  performance: {
    baselines: () => client.get('/plt/performance/baselines'),
    createBaseline: (data: any) => client.post('/plt/performance/baselines', data),
    regressionCheck: () => client.get('/plt/performance/regression-check'),
  },
  cicd: {
    pipelines: () => client.get('/plt/cicd/pipelines'),
    deploy: (data: any) => client.post('/plt/cicd/deploy', data),
    rollback: (deploymentId: string) => client.post(`/plt/cicd/rollback/${deploymentId}`),
  },
}