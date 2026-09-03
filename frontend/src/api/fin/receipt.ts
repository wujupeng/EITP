import { client } from '../client'

export const receiptApi = {
  confirm: (receiptNo: string, data: any) =>
    client.post('/fin/receipts', data, { params: { receipt_no: receiptNo } }),
  writeOff: (id: string, data: any) => client.post(`/fin/receipts/${id}/write-off`, data),
  get: (id: string) => client.get(`/fin/receipts/${id}`),
  list: (params?: any) => client.get('/fin/receipts', { params }),
}

export const collectionTaskApi = {
  list: (params?: any) => client.get('/fin/collection-tasks', { params }),
  handle: (id: string, data: any) => client.post(`/fin/collection-tasks/${id}/handle`, data),
}
