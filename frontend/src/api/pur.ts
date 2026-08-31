import { client } from './client'
import type {
  ApproveRequest, Asn, CreateAsnRequest, CreateInvoiceRequest,
  CreatePurchaseOrderRequest, CreatePurchaseRequestRequest,
  CreatePurchaseReturnRequest, CreateReceiptRequest, CreateSettlementRequest,
  CreateSupplierRequest, CreateQuotationRequest, IdResult, Invoice,
  PaymentRequest, PurchaseOrder, PurchaseReceipt, PurchaseRequest,
  PurchaseReturn, PurchaseSettlement, Quotation, ReconcileDiff, ReceiptConfirmRequest,
  Supplier, SupplierEvaluation, SupplierEvaluationRequest, SupplierScope, SupplierScopeRequest,
} from '@/types/pur'

export const purApi = {
  suppliers: {
    async create(payload: CreateSupplierRequest): Promise<IdResult> {
      const { data } = await client.post('/pur/suppliers', payload)
      return data
    },
    async list(offset = 0, limit = 50): Promise<Supplier[]> {
      const { data } = await client.get('/pur/suppliers', { params: { offset, limit } })
      return data
    },
    async get(supplierId: string): Promise<Supplier> {
      const { data } = await client.get(`/pur/suppliers/${supplierId}`)
      return data
    },
    async patch(supplierId: string, payload: Partial<CreateSupplierRequest>): Promise<IdResult> {
      const { data } = await client.patch(`/pur/suppliers/${supplierId}`, payload)
      return data
    },
    async submit(supplierId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/suppliers/${supplierId}/submit`)
      return data
    },
    async approve(supplierId: string, payload: ApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/pur/suppliers/${supplierId}/approve`, payload)
      return data
    },
    async publish(supplierId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/suppliers/${supplierId}/publish`)
      return data
    },
    async disable(supplierId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/suppliers/${supplierId}/disable`)
      return data
    },
    async addScope(supplierId: string, payload: SupplierScopeRequest): Promise<IdResult> {
      const { data } = await client.post(`/pur/suppliers/${supplierId}/scopes`, payload)
      return data
    },
    async getScopes(supplierId: string): Promise<SupplierScope[]> {
      const { data } = await client.get(`/pur/suppliers/${supplierId}/scopes`)
      return data
    },
    async addEvaluation(supplierId: string, payload: SupplierEvaluationRequest): Promise<IdResult> {
      const { data } = await client.post(`/pur/suppliers/${supplierId}/evaluations`, payload)
      return data
    },
    async listEvaluations(supplierId: string): Promise<SupplierEvaluation[]> {
      const { data } = await client.get(`/pur/suppliers/${supplierId}/evaluations`)
      return data
    },
  },

  quotations: {
    async create(payload: CreateQuotationRequest): Promise<IdResult> {
      const { data } = await client.post('/pur/quotations', payload)
      return data
    },
    async list(supplierId?: string): Promise<Quotation[]> {
      const { data } = await client.get('/pur/quotations', { params: { supplier_id: supplierId } })
      return data
    },
    async submit(quotationId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/quotations/${quotationId}/submit`)
      return data
    },
    async approve(quotationId: string, payload: ApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/pur/quotations/${quotationId}/approve`, payload)
      return data
    },
    async publish(quotationId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/quotations/${quotationId}/publish`)
      return data
    },
  },

  requests: {
    async create(payload: CreatePurchaseRequestRequest): Promise<IdResult> {
      const { data } = await client.post('/pur/requests', payload)
      return data
    },
    async list(offset = 0, limit = 50): Promise<PurchaseRequest[]> {
      const { data } = await client.get('/pur/requests', { params: { offset, limit } })
      return data
    },
    async get(requestId: string): Promise<Record<string, unknown>> {
      const { data } = await client.get(`/pur/requests/${requestId}`)
      return data
    },
    async submit(requestId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/requests/${requestId}/submit`)
      return data
    },
    async approve(requestId: string, payload: ApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/pur/requests/${requestId}/approve`, payload)
      return data
    },
    async convert(requestId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/requests/${requestId}/convert`)
      return data
    },
    async cancel(requestId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/requests/${requestId}/cancel`)
      return data
    },
  },

  orders: {
    async create(payload: CreatePurchaseOrderRequest): Promise<IdResult> {
      const { data } = await client.post('/pur/orders', payload)
      return data
    },
    async list(params?: { supplier_id?: string; status?: string; offset?: number; limit?: number }): Promise<PurchaseOrder[]> {
      const { data } = await client.get('/pur/orders', { params })
      return data
    },
    async get(orderId: string): Promise<Record<string, unknown>> {
      const { data } = await client.get(`/pur/orders/${orderId}`)
      return data
    },
    async submit(orderId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/orders/${orderId}/submit`)
      return data
    },
    async approve(orderId: string, payload: ApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/pur/orders/${orderId}/approve`, payload)
      return data
    },
    async send(orderId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/orders/${orderId}/send`)
      return data
    },
    async change(orderId: string, payload: { reason: string; lines: unknown[] }): Promise<IdResult> {
      const { data } = await client.post(`/pur/orders/${orderId}/change`, payload)
      return data
    },
    async cancel(orderId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/orders/${orderId}/cancel`)
      return data
    },
    async close(orderId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/orders/${orderId}/close`)
      return data
    },
    async trace(orderId: string): Promise<Record<string, unknown>> {
      const { data } = await client.get(`/pur/orders/${orderId}/trace`)
      return data
    },
  },

  asns: {
    async create(payload: CreateAsnRequest): Promise<IdResult> {
      const { data } = await client.post('/pur/asns', payload)
      return data
    },
    async list(orderId?: string): Promise<Asn[]> {
      const { data } = await client.get('/pur/asns', { params: { order_id: orderId } })
      return data
    },
    async arrive(asnId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/asns/${asnId}/arrive`, { arrived: true })
      return data
    },
  },

  receipts: {
    async create(payload: CreateReceiptRequest): Promise<IdResult> {
      const { data } = await client.post('/pur/receipts', payload)
      return data
    },
    async list(orderId?: string): Promise<PurchaseReceipt[]> {
      const { data } = await client.get('/pur/receipts', { params: { order_id: orderId } })
      return data
    },
    async confirm(receiptId: string, payload: ReceiptConfirmRequest): Promise<IdResult> {
      const { data } = await client.post(`/pur/receipts/${receiptId}/confirm`, payload)
      return data
    },
    async qc(receiptId: string, payload: { line_id: string; qc_result: string; qc_note?: string }): Promise<IdResult> {
      const { data } = await client.post(`/pur/receipts/${receiptId}/qc`, payload)
      return data
    },
    async get(receiptId: string): Promise<PurchaseReceipt> {
      const { data } = await client.get(`/pur/receipts/${receiptId}`)
      return data
    },
  },

  returns: {
    async create(payload: CreatePurchaseReturnRequest): Promise<IdResult> {
      const { data } = await client.post('/pur/returns', payload)
      return data
    },
    async list(orderId?: string): Promise<PurchaseReturn[]> {
      const { data } = await client.get('/pur/returns', { params: { order_id: orderId } })
      return data
    },
    async submit(returnId: string): Promise<IdResult> {
      const { data } = await client.post(`/pur/returns/${returnId}/submit`)
      return data
    },
    async approve(returnId: string, payload: ApproveRequest): Promise<IdResult> {
      const { data } = await client.post(`/pur/returns/${returnId}/approve`, payload)
      return data
    },
    async ship(returnId: string, payload: { via_wms_shipping?: boolean; idempotency_key?: string }): Promise<IdResult> {
      const { data } = await client.post(`/pur/returns/${returnId}/ship`, payload)
      return data
    },
    async get(returnId: string): Promise<PurchaseReturn> {
      const { data } = await client.get(`/pur/returns/${returnId}`)
      return data
    },
  },

  settlements: {
    async create(payload: CreateSettlementRequest): Promise<IdResult> {
      const { data } = await client.post('/pur/settlements', payload)
      return data
    },
    async list(orderId?: string): Promise<PurchaseSettlement[]> {
      const { data } = await client.get('/pur/settlements', { params: { order_id: orderId } })
      return data
    },
    async reconcile(settlementId: string, payload: { received_amount: number }): Promise<IdResult> {
      const { data } = await client.post(`/pur/settlements/${settlementId}/reconcile`, payload)
      return data
    },
    async matchInvoice(settlementId: string, payload: { invoice_id: string; matched_amount: number }): Promise<IdResult> {
      const { data } = await client.post(`/pur/settlements/${settlementId}/match-invoice`, payload)
      return data
    },
    async requestPayment(settlementId: string, payload: { payment_code: string; amount: number }): Promise<IdResult> {
      const { data } = await client.post(`/pur/settlements/${settlementId}/request-payment`, payload)
      return data
    },
    async get(settlementId: string): Promise<PurchaseSettlement> {
      const { data } = await client.get(`/pur/settlements/${settlementId}`)
      return data
    },
  },

  invoices: {
    async create(payload: CreateInvoiceRequest): Promise<IdResult> {
      const { data } = await client.post('/pur/invoices', payload)
      return data
    },
    async list(supplierId?: string): Promise<Invoice[]> {
      const { data } = await client.get('/pur/invoices', { params: { supplier_id: supplierId } })
      return data
    },
    async match(invoiceId: string, payload: { settlement_id: string; matched_amount: number }): Promise<IdResult> {
      const { data } = await client.post(`/pur/invoices/${invoiceId}/match`, payload)
      return data
    },
  },

  payments: {
    async list(settlementId?: string): Promise<PaymentRequest[]> {
      const { data } = await client.get('/pur/payments', { params: { settlement_id: settlementId } })
      return data
    },
    async confirm(paymentId: string, payload: { paid: boolean }): Promise<IdResult> {
      const { data } = await client.post(`/pur/payments/${paymentId}/confirm`, payload)
      return data
    },
  },

  reconcile: {
    async run(orderId: string): Promise<Record<string, unknown>> {
      const { data } = await client.post('/pur/reconcile/run', { order_id: orderId })
      return data
    },
    async listDiffs(): Promise<ReconcileDiff[]> {
      const { data } = await client.get('/pur/reconcile/diffs')
      return data
    },
    async repair(diffId: string, repairNote?: string): Promise<IdResult> {
      const { data } = await client.post('/pur/reconcile/repair', { diff_id: diffId, repair_note: repairNote })
      return data
    },
  },
}