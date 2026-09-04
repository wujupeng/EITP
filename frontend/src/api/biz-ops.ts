import { client } from './client'

// ==================== 功能开关 ====================

export const featureSwitchApi = {
  list: () => client.get('/biz-ops/strategies/feature-switches'),
  get: (key: string) => client.get(`/biz-ops/strategies/feature-switches/${key}`),
  create: (data: any) => client.post('/biz-ops/strategies/feature-switches', data),
  update: (key: string, data: any) => client.put(`/biz-ops/strategies/feature-switches/${key}`, data),
}

// ==================== 业务规则 ====================

export const businessRuleApi = {
  list: () => client.get('/biz-ops/strategies/business-rules'),
  create: (data: any) => client.post('/biz-ops/strategies/business-rules', data),
  update: (key: string, data: any) => client.put(`/biz-ops/strategies/business-rules/${key}`, data),
  activate: (key: string) => client.post(`/biz-ops/strategies/business-rules/${key}/activate`),
  deactivate: (key: string) => client.post(`/biz-ops/strategies/business-rules/${key}/deactivate`),
}

// ==================== 定价策略 ====================

export const pricingStrategyApi = {
  list: () => client.get('/biz-ops/strategies/pricing'),
  get: (key: string) => client.get(`/biz-ops/strategies/pricing/${key}`),
  create: (data: any) => client.post('/biz-ops/strategies/pricing', data),
  update: (key: string, data: any) => client.put(`/biz-ops/strategies/pricing/${key}`, data),
}

// ==================== 税务配置 ====================

export const taxConfigApi = {
  list: () => client.get('/biz-ops/strategies/tax-configs'),
  create: (data: any) => client.post('/biz-ops/strategies/tax-configs', data),
  update: (key: string, data: any) => client.put(`/biz-ops/strategies/tax-configs/${key}`, data),
  calculate: (data: any) => client.post('/biz-ops/operations/tax/calculate', data),
}

// ==================== 库存策略 ====================

export const inventoryStrategyApi = {
  list: () => client.get('/biz-ops/strategies/inventory-strategies'),
  create: (data: any) => client.post('/biz-ops/strategies/inventory-strategies', data),
  update: (key: string, data: any) => client.put(`/biz-ops/strategies/inventory-strategies/${key}`, data),
  alerts: () => client.get('/biz-ops/operations/inventory/strategies/alerts'),
  suggestions: () => client.get('/biz-ops/operations/inventory/strategies/replenish-suggestions'),
}

// ==================== 审批操作 ====================

export const approvalApi = {
  approve: (id: string, data: any) => client.post(`/biz-ops/operations/approvals/${id}/approve`, data),
  reject: (id: string, data: any) => client.post(`/biz-ops/operations/approvals/${id}/reject`, data),
  return: (id: string, data: any) => client.post(`/biz-ops/operations/approvals/${id}/return`, data),
  addSign: (id: string, data: any) => client.post(`/biz-ops/operations/approvals/${id}/add-sign`, data),
  transfer: (id: string, data: any) => client.post(`/biz-ops/operations/approvals/${id}/transfer`, data),
  delegate: (id: string, data: any) => client.post(`/biz-ops/operations/approvals/${id}/delegate`, data),
  pending: () => client.get('/biz-ops/operations/approvals/pending'),
}

// ==================== 业务操作编排 ====================

export const operationApi = {
  purchase: {
    createOrder: (data: any) => client.post('/biz-ops/operations/purchase/orders', data),
    submitOrder: (data: any) => client.post('/biz-ops/operations/purchase/orders/submit', data),
    approveOrder: (data: any) => client.post('/biz-ops/operations/purchase/orders/approve', data),
    receipt: (data: any) => client.post('/biz-ops/operations/purchase/receipts', data),
    return: (data: any) => client.post('/biz-ops/operations/purchase/returns', data),
  },
  sales: {
    createOrder: (data: any) => client.post('/biz-ops/operations/sales/orders', data),
    submitOrder: (data: any) => client.post('/biz-ops/operations/sales/orders/submit', data),
    shipment: (data: any) => client.post('/biz-ops/operations/sales/shipments', data),
    return: (data: any) => client.post('/biz-ops/operations/sales/returns', data),
  },
  inventory: {
    inbound: (data: any) => client.post('/biz-ops/operations/inventory/inbound', data),
    outbound: (data: any) => client.post('/biz-ops/operations/inventory/outbound', data),
    transfer: (data: any) => client.post('/biz-ops/operations/inventory/transfers', data),
    count: (data: any) => client.post('/biz-ops/operations/inventory/counts', data),
    adjust: (data: any) => client.post('/biz-ops/operations/inventory/adjustments', data),
  },
  warehouse: {
    receiving: (data: any) => client.post('/biz-ops/operations/warehouse/receiving', data),
    putaway: (data: any) => client.post('/biz-ops/operations/warehouse/putaway', data),
    picking: (data: any) => client.post('/biz-ops/operations/warehouse/picking', data),
    transfer: (data: any) => client.post('/biz-ops/operations/warehouse/transfers', data),
    shipping: (data: any) => client.post('/biz-ops/operations/warehouse/shipping', data),
  },
}

// ==================== 审计查询 ====================

export const auditApi = {
  operations: (params?: any) => client.get('/biz-ops/audits/operations', { params }),
  strategies: (params?: any) => client.get('/biz-ops/audits/strategies', { params }),
  approvals: (params?: any) => client.get('/biz-ops/audits/approvals', { params }),
}