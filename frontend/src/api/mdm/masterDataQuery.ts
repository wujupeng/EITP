import { client } from '../client'
import type { MasterDataQueryResult, BarcodeLocateResult } from './types'

export const masterDataQueryApi = {
  async query(params: {
    enterprise_product_code?: string
    group_product_id?: string
    limit?: number
  }): Promise<MasterDataQueryResult[]> {
    const { data } = await client.get('/tenant/mdm/master-data:query', { params })
    return data
  },

  async get(enterpriseProductId: string): Promise<MasterDataQueryResult> {
    const { data } = await client.get(`/tenant/mdm/master-data/${enterpriseProductId}`)
    return data
  },

  async locateByBarcode(barcode: string): Promise<BarcodeLocateResult> {
    const { data } = await client.get('/tenant/mdm/skus:locate-by-barcode', { params: { barcode } })
    return data
  },
}