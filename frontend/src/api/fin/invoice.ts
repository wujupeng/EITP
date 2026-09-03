import { client } from '../client'

export const invoiceApi = {
  issue: (data: any) => client.post('/fin/invoices', data),
  match: (id: string, data: any) => client.post(`/fin/invoices/${id}/match`, data),
  verify: (id: string) => client.post(`/fin/invoices/${id}/verify`),
  archive: (id: string) => client.post(`/fin/invoices/${id}/archive`),
  void: (id: string, data: any) => client.post(`/fin/invoices/${id}/void`, data),
  get: (id: string) => client.get(`/fin/invoices/${id}`),
  list: (params?: any) => client.get('/fin/invoices', { params }),
}