import { client } from '../client'

export const settlementApi = {
  create: (data: any) => client.post('/fin/settlements', data),
  confirm: (id: string) => client.post(`/fin/settlements/${id}/confirm`),
  cancel: (id: string, data: any) => client.post(`/fin/settlements/${id}/cancel`, data),
  get: (id: string) => client.get(`/fin/settlements/${id}`),
  list: (params?: any) => client.get('/fin/settlements', { params }),
  crossTenantConfirm: (id: string) => client.post(`/fin/settlements/cross-tenant/${id}/confirm`),
}