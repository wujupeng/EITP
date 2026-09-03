import { client } from '../client'

export const reconciliationApi = {
  create: (data: any) => client.post('/fin/reconciliations', data),
  handleDifference: (reconNo: string, diffId: string, data: any) =>
    client.post(`/fin/reconciliations/${reconNo}/differences/${diffId}/handle`, data),
  report: (id: string) => client.get(`/fin/reconciliations/${id}/report`),
  get: (id: string) => client.get(`/fin/reconciliations/${id}`),
  list: (params?: any) => client.get('/fin/reconciliations', { params }),
}
