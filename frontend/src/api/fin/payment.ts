import { client } from '../client'

export const paymentApi = {
  request: (data: any) => client.post('/fin/payments', data),
  approve: (id: string, data: any) => client.post(`/fin/payments/${id}/approve`, data),
  execute: (id: string) => client.post(`/fin/payments/${id}/execute`),
  bankCallback: (paymentNo: string, data: any) =>
    client.post(`/fin/payments/${paymentNo}/bank-callback`, data),
  get: (id: string) => client.get(`/fin/payments/${id}`),
  list: (params?: any) => client.get('/fin/payments', { params }),
  importBankStatement: (data: any) => client.post('/fin/payments/bank-statement/import', data),
}
