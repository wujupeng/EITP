import { client } from '../client'

export const accountingApi = {
  arVouchers: {
    list: (params?: any) => client.get('/fin/accounting/ar-vouchers', { params }),
  },
  apVouchers: {
    list: (params?: any) => client.get('/fin/accounting/ap-vouchers', { params }),
  },
  agingAnalysis: (params?: any) => client.get('/fin/accounting/aging-analysis', { params }),
  glAccounts: {
    list: (params?: any) => client.get('/fin/accounting/gl-accounts', { params }),
    create: (data: any) => client.post('/fin/accounting/gl-accounts', data),
  },
  glVouchers: {
    list: (params?: any) => client.get('/fin/accounting/gl-vouchers', { params }),
    create: (data: any) => client.post('/fin/accounting/gl-vouchers', data),
  },
  redVoucher: (id: string, data: any) => client.post(`/fin/accounting/gl-vouchers/${id}/red`, data),
  periodClose: (data: any) => client.post('/fin/accounting/period-close', data),
  reports: (reportType: string, params?: any) => client.get(`/fin/accounting/reports/${reportType}`, { params }),
}
