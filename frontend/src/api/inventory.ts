import { client } from './client'

export interface Product {
  id: string
  product_code: string
  product_name: string
  status: string
}

export interface InventoryBalance {
  id: string
  sku_id: string
  warehouse_id: string
  on_hand: number
  reserved: number
  available: number
  in_transit: number
  inspection: number
  blocked: number
  unit_cost: number
}

export interface InventoryLedger {
  id: string
  transaction_id: string
  transaction_type: string
  direction: string
  quantity_before: number
  quantity_change: number
  quantity_after: number
  operated_at: string
}

export interface InventoryTransactionResult {
  id: string
  transaction_type: string
  quantity: number
  status: string
  result_ledger_id: string | null
}

export const inventoryApi = {
  async listProducts(limit = 100, offset = 0): Promise<Product[]> {
    const { data } = await client.get('/inv/products', { params: { limit, offset } })
    return data
  },

  async createProduct(payload: {
    product_code: string
    product_name: string
    description?: string
  }): Promise<Product> {
    const { data } = await client.post('/inv/products', payload)
    return data
  },

  async queryBalance(params?: { sku_id?: string; warehouse_id?: string }): Promise<InventoryBalance[]> {
    const { data } = await client.get('/inv/inventory/query/balance', { params })
    return data
  },

  async queryLedger(params: { sku_id: string; warehouse_id: string; limit?: number }): Promise<InventoryLedger[]> {
    const { data } = await client.get('/inv/inventory/query/ledger', { params })
    return data
  },

  async executeTransaction(payload: {
    sku_id: string
    warehouse_id: string
    transaction_type: string
    quantity: number
    idempotency_key: string
    unit_cost?: number
    reason?: string
  }): Promise<InventoryTransactionResult> {
    const { data } = await client.post('/inv/inventory/transactions', payload)
    return data
  },

  async listDocuments(limit = 100, offset = 0): Promise<any[]> {
    const { data } = await client.get('/inv/documents', { params: { limit, offset } })
    return data
  },
}