import { client } from './client'

export const relApi = {
  seal: {
    request: (data: any) => client.post('/rel/seals', data),
    executeGates: (releaseId: string, executedBy: string) =>
      client.post(`/rel/seals/${releaseId}/execute-gates`, null, { params: { executed_by: executedBy } }),
    collectSnapshots: (releaseId: string, collectedBy: string) =>
      client.post(`/rel/seals/${releaseId}/collect-snapshots`, null, { params: { collected_by: collectedBy } }),
    assembleReport: (releaseId: string, executedBy: string) =>
      client.post(`/rel/seals/${releaseId}/assemble-report`, null, { params: { executed_by: executedBy } }),
    coSign: (releaseId: string, data: any) => client.post(`/rel/seals/${releaseId}/co-sign`, data),
    get: (releaseId: string) => client.get(`/rel/seals/${releaseId}`),
    list: (params?: any) => client.get('/rel/seals', { params }),
  },
  gate: {
    list: (releaseId: string) => client.get(`/rel/gates/${releaseId}`),
    retry: (releaseId: string, data: any) => client.post(`/rel/gates/${releaseId}/retry`, data),
  },
  snapshot: {
    list: (releaseId: string) => client.get(`/rel/snapshots/${releaseId}`),
    get: (releaseId: string, snapshotId: string) =>
      client.get(`/rel/snapshots/${releaseId}/${snapshotId}`),
    verifyHash: (releaseId: string) => client.post(`/rel/snapshots/${releaseId}/verify-hash`),
  },
  declaration: {
    issue: (releaseId: string) => client.post(`/rel/declarations/${releaseId}/issue`),
    get: (releaseId: string) => client.get(`/rel/declarations/${releaseId}`),
    list: (params?: any) => client.get('/rel/declarations', { params }),
  },
  report: {
    assemble: (releaseId: string, executedBy: string) =>
      client.post(`/rel/reports/${releaseId}/assemble`, null, { params: { executed_by: executedBy } }),
    get: (releaseId: string) => client.get(`/rel/reports/${releaseId}`),
    getVerdict: (releaseId: string) => client.get(`/rel/reports/${releaseId}/verdict`),
  },
  rollback: {
    get: (releaseId: string) => client.get(`/rel/rollback-plans/${releaseId}`),
    drill: (releaseId: string, data: any) => client.post(`/rel/rollback-plans/${releaseId}/drill`, data),
    updateDrillResult: (releaseId: string, data: any) =>
      client.post(`/rel/rollback-plans/${releaseId}/drill-result`, data),
  },
}