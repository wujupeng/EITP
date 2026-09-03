import { client } from '../client'

export const accountingApi = {
  arVouchers: {
    list: (params?: any) => client.get('/fin/accounting/ar-vouchers', { params }),
    get: (id: string) => client.get(`/fin/accounting/ar-vouchers/${id}`),
  },
  apVouchers: {
    list: (params?: any) => client.get('/fin/accounting/ap-vouchers', { params }),
    get: (id: string) => client.get(`/fin/accounting/ap-vouchers/${id}`),
  },
  agingAnalysis: (params?: any) => client.get('/fin/accounting/aging-analysis', { params }),
  glAccounts: {
    list: (params?: any) => client.get('/fin/accounting/gl-accounts', { params }),
    create: (data: any) => client.post('/fin/accounting/gl-accounts', data),
  },
  glVouchers: {
    list: (params?: any) => client.get('/fin/accounting/gl-vouchers', { params }),
    get: (id: string) => client.get(`/fin/accounting/gl-vouchers/${id}`),
    create: (data: any) => client.post('/fin/accounting/gl-vouchers', data),
  },
  redVoucher: (id: string, data: any) => client.post(`/fin/accounting/gl-vouchers/${id}/red`, data),
  periodClose: (data: any) => client.post('/fin/accounting/period-close', data),
  reports: (params?: any) => client.get('/fin/accounting/reports', { params }),
}