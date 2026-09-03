import { client } from '../client'

export const reconciliationApi = {
  create: (data: any) => client.post('/fin/reconciliations', data),
  handleDifference: (id: string, data: any) => client.post(`/fin/reconciliations/${id}/difference`, data),
  report: (id: string) => client.get(`/fin/reconciliations/${id}/report`),
  get: (id: string) => client.get(`/fin/reconciliations/${id}`),
  list: (params?: any) => client.get('/fin/reconciliations', { params }),
}