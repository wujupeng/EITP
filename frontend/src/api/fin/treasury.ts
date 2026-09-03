import { client } from '../client'

export const treasuryApi = {
  accounts: {
    list: (params?: any) => client.get('/fin/treasury/accounts', { params }),
    get: (id: string) => client.get(`/fin/treasury/accounts/${id}/balance`),
  },
  balance: (params?: any) => client.get('/fin/treasury/balance', { params }),
  transfers: {
    list: (params?: any) => client.get('/fin/treasury/transfers', { params }),
    create: (data: any) => client.post('/fin/treasury/transfers', data),
  },
  approve: (id: string, data: any) => client.post(`/fin/treasury/transfers/${id}/approve`, data),
  freeze: (id: string, data: any) => client.post(`/fin/treasury/accounts/${id}/freeze`, data),
  forecast: (params?: any) => client.get('/fin/treasury/forecast', { params }),
}
