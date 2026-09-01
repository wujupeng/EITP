import { client } from './client'
import type {
  ApproveRequest, ChangeSalesOrderRequest, CreateCustomerCategoryRequest,
  CreateCustomerRequest, CreatePackingRequest, CreateSalesInvoiceRequest,
  CreateSalesOrderRequest, CreateSalesQuotationRequest, CreateSalesReturnRequest,
  CreateSalesSettlementRequest, CreateShipmentRequest, CreditLimit, Customer,
  CustomerCategory, CustomerPricing, IdResult, InvoiceMatchRequest, MatchInvoiceRequest,
  PackingRecord, PaymentConfirmRequest, PaymentReceipt, ReconcileDiff, RequestPaymentRequest,
  ReturnDisposeRequest, ReturnQcRequest, SalesInvoice, SalesOrder, SalesOrderLine,
  SalesQuotation, SalesReturn, SalesSettlement, SetCreditLimitRequest,
  SetCustomerPricingRequest, SettlementReconcileRequest, ShipmentConfirmRequest,
  ShipmentOrder,
} from '@/types/sal'

export const salApi = {
  customers: {
    async create(payload: CreateCustomerRequest): Promise<IdResult> {
      const { data } = await client.post('/sal/customers', payload)
      return data
    },
    async list(offset = 0, limit = 50): Promise<Customer[]> {
      const { data } = await client.get('/sal/customers', { params: { offset, limit } })
      return data
    },
    async get(customerId: string): Promise<Customer> {
      const { data } = await client.get(`/sal/customers/${customerId}`)
      return data
    },
    async patch(customerId: string, payload: Partial<CreateCustomerRequest>): Promise<IdResult> {
      const { data } = await client.patch(`/sal/customers/${customerId}`, payload)
      return data
    },
    async submit(customerId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/customers/${customerId}/submit`)
      return data
    },
    async approve(customerId: string, payload: ApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/customers/${customerId}/approve`, payload)
      return data
    },
    async publish(customerId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/customers/${customerId}/publish`)
      return data
    },
    async disable(customerId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/customers/${customerId}/disable`)
      return data
    },
    async setCreditLimit(customerId: string, payload: SetCreditLimitRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/customers/${customerId}/credit-limit`, payload)
      return data
    },
    async getCreditLimit(customerId: string): Promise<CreditLimit> {
      const { data } = await client.get(`/sal/customers/${customerId}/credit-limit`)
      return data
    },
    async setPricing(customerId: string, payload: SetCustomerPricingRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/customers/${customerId}/pricings`, payload)
      return data
    },
    async getPricings(customerId: string): Promise<CustomerPricing[]> {
      const { data } = await client.get(`/sal/customers/${customerId}/pricings`)
      return data
    },
  },

  categories: {
    async create(payload: CreateCustomerCategoryRequest): Promise<IdResult> {
      const { data } = await client.post('/sal/customer-categories', payload)
      return data
    },
    async list(): Promise<CustomerCategory[]> {
      const { data } = await client.get('/sal/customer-categories')
      return data
    },
    async patch(categoryId: string, payload: Partial<CreateCustomerCategoryRequest>): Promise<IdResult> {
      const { data } = await client.patch(`/sal/customer-categories/${categoryId}`, payload)
      return data
    },
    async disable(categoryId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/customer-categories/${categoryId}/disable`)
      return data
    },
  },

  credit: {
    async get(customerId: string): Promise<CreditLimit> {
      const { data } = await client.get(`/sal/customers/${customerId}/credit-limit`)
      return data
    },
    async set(customerId: string, payload: SetCreditLimitRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/customers/${customerId}/credit-limit`, payload)
      return data
    },
  },

  pricing: {
    async list(customerId: string): Promise<CustomerPricing[]> {
      const { data } = await client.get(`/sal/customers/${customerId}/pricings`)
      return data
    },
    async set(customerId: string, payload: SetCustomerPricingRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/customers/${customerId}/pricings`, payload)
      return data
    },
  },

  quotations: {
    async create(payload: CreateSalesQuotationRequest): Promise<IdResult> {
      const { data } = await client.post('/sal/quotations', payload)
      return data
    },
    async list(customerId?: string): Promise<SalesQuotation[]> {
      const { data } = await client.get('/sal/quotations', { params: { customer_id: customerId } })
      return data
    },
    async get(quotationId: string): Promise<SalesQuotation> {
      const { data } = await client.get(`/sal/quotations/${quotationId}`)
      return data
    },
    async submit(quotationId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/quotations/${quotationId}/submit`)
      return data
    },
    async approve(quotationId: string, payload: ApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/quotations/${quotationId}/approve`, payload)
      return data
    },
    async convert(quotationId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/quotations/${quotationId}/convert`)
      return data
    },
    async cancel(quotationId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/quotations/${quotationId}/cancel`)
      return data
    },
  },

  orders: {
    async create(payload: CreateSalesOrderRequest): Promise<IdResult> {
      const { data } = await client.post('/sal/orders', payload)
      return data
    },
    async list(params?: { customer_id?: string; status?: string; offset?: number; limit?: number }): Promise<SalesOrder[]> {
      const { data } = await client.get('/sal/orders', { params })
      return data
    },
    async get(orderId: string): Promise<SalesOrder> {
      const { data } = await client.get(`/sal/orders/${orderId}`)
      return data
    },
    async getLines(orderId: string): Promise<SalesOrderLine[]> {
      const { data } = await client.get(`/sal/orders/${orderId}/lines`)
      return data
    },
    async patch(orderId: string, payload: Partial<CreateSalesOrderRequest>): Promise<IdResult> {
      const { data } = await client.patch(`/sal/orders/${orderId}`, payload)
      return data
    },
    async submit(orderId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/orders/${orderId}/submit`)
      return data
    },
    async approve(orderId: string, payload: ApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/orders/${orderId}/approve`, payload)
      return data
    },
    async confirm(orderId: string, payload?: { idempotency_key?: string }): Promise<IdResult> {
      const { data } = await client.post(`/sal/orders/${orderId}/confirm`, payload)
      return data
    },
    async change(orderId: string, payload: ChangeSalesOrderRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/orders/${orderId}/change`, payload)
      return data
    },
    async cancel(orderId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/orders/${orderId}/cancel`)
      return data
    },
    async close(orderId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/orders/${orderId}/close`)
      return data
    },
    async trace(orderId: string): Promise<Record<string, unknown>> {
      const { data } = await client.get(`/sal/orders/${orderId}/trace`)
      return data
    },
  },

  shipments: {
    async create(payload: CreateShipmentRequest): Promise<IdResult> {
      const { data } = await client.post('/sal/shipments', payload)
      return data
    },
    async list(orderId?: string): Promise<ShipmentOrder[]> {
      const { data } = await client.get('/sal/shipments', { params: { order_id: orderId } })
      return data
    },
    async get(shipmentId: string): Promise<ShipmentOrder> {
      const { data } = await client.get(`/sal/shipments/${shipmentId}`)
      return data
    },
    async submit(shipmentId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/shipments/${shipmentId}/submit`)
      return data
    },
    async confirm(shipmentId: string, payload: ShipmentConfirmRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/shipments/${shipmentId}/confirm`, payload)
      return data
    },
    async cancel(shipmentId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/shipments/${shipmentId}/cancel`)
      return data
    },
  },

  packing: {
    async create(payload: CreatePackingRequest): Promise<IdResult> {
      const { data } = await client.post('/sal/packing', payload)
      return data
    },
    async get(packingId: string): Promise<PackingRecord> {
      const { data } = await client.get(`/sal/packing/${packingId}`)
      return data
    },
    async listByShipment(shipmentId: string): Promise<PackingRecord[]> {
      const { data } = await client.get(`/sal/shipments/${shipmentId}/packing`)
      return data
    },
    async complete(packingId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/packing/${packingId}/complete`)
      return data
    },
  },

  returns: {
    async create(payload: CreateSalesReturnRequest): Promise<IdResult> {
      const { data } = await client.post('/sal/returns', payload)
      return data
    },
    async list(orderId?: string): Promise<SalesReturn[]> {
      const { data } = await client.get('/sal/returns', { params: { order_id: orderId } })
      return data
    },
    async get(returnId: string): Promise<SalesReturn> {
      const { data } = await client.get(`/sal/returns/${returnId}`)
      return data
    },
    async submit(returnId: string): Promise<IdResult> {
      const { data } = await client.post(`/sal/returns/${returnId}/submit`)
      return data
    },
    async approve(returnId: string, payload: ApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/returns/${returnId}/approve`, payload)
      return data
    },
    async receive(returnId: string, payload: { idempotency_key?: string }): Promise<IdResult> {
      const { data } = await client.post(`/sal/returns/${returnId}/receive`, payload)
      return data
    },
    async qc(returnId: string, payload: ReturnQcRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/returns/${returnId}/qc`, payload)
      return data
    },
    async dispose(returnId: string, payload: ReturnDisposeRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/returns/${returnId}/dispose`, payload)
      return data
    },
  },

  settlements: {
    async create(payload: CreateSalesSettlementRequest): Promise<IdResult> {
      const { data } = await client.post('/sal/settlements', payload)
      return data
    },
    async list(orderId?: string): Promise<SalesSettlement[]> {
      const { data } = await client.get('/sal/settlements', { params: { order_id: orderId } })
      return data
    },
    async get(settlementId: string): Promise<SalesSettlement> {
      const { data } = await client.get(`/sal/settlements/${settlementId}`)
      return data
    },
    async reconcile(settlementId: string, payload: SettlementReconcileRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/settlements/${settlementId}/reconcile`, payload)
      return data
    },
    async matchInvoice(settlementId: string, payload: MatchInvoiceRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/settlements/${settlementId}/match-invoice`, payload)
      return data
    },
    async requestPayment(settlementId: string, payload: RequestPaymentRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/settlements/${settlementId}/request-payment`, payload)
      return data
    },
  },

  invoices: {
    async create(payload: CreateSalesInvoiceRequest): Promise<IdResult> {
      const { data } = await client.post('/sal/invoices', payload)
      return data
    },
    async list(customerId?: string): Promise<SalesInvoice[]> {
      const { data } = await client.get('/sal/invoices', { params: { customer_id: customerId } })
      return data
    },
    async match(invoiceId: string, payload: InvoiceMatchRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/invoices/${invoiceId}/match`, payload)
      return data
    },
  },

  payments: {
    async list(settlementId?: string): Promise<PaymentReceipt[]> {
      const { data } = await client.get('/sal/payments', { params: { settlement_id: settlementId } })
      return data
    },
    async confirm(paymentId: string, payload: PaymentConfirmRequest): Promise<IdResult> {
      const { data } = await client.post(`/sal/payments/${paymentId}/confirm`, payload)
      return data
    },
  },

  reconcile: {
    async run(orderId: string): Promise<Record<string, unknown>> {
      const { data } = await client.post('/sal/reconcile/run', { order_id: orderId })
      return data
    },
    async listDiffs(): Promise<ReconcileDiff[]> {
      const { data } = await client.get('/sal/reconcile/diffs')
      return data
    },
    async repair(diffId: string, repairNote?: string): Promise<IdResult> {
      const { data } = await client.post('/sal/reconcile/repair', { diff_id: diffId, repair_note: repairNote })
      return data
    },
  },
}