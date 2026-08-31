export type SupplierType = 'distributor' | 'manufacturer' | 'agent' | 'individual'
export type SupplierStatus = 'draft' | 'submitted' | 'approved' | 'active' | 'disabled'
export type GovernanceState = 'draft' | 'submitted' | 'approved' | 'rejected' | 'published'
export type QuotationStatus = 'draft' | 'submitted' | 'approved' | 'active' | 'expired'
export type SupplierGrade = 'excellent' | 'qualified' | 'unqualified'
export type RequestStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'converted' | 'cancelled'
export type OrderStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'sent' | 'receiving' | 'completed' | 'cancelled' | 'closed'
export type AsnStatus = 'pending' | 'arrived' | 'cancelled'
export type ReceiptStatus = 'pending' | 'confirmed' | 'failed'
export type QcResult = 'pending' | 'passed' | 'failed' | 'conditional'
export type ReturnStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'shipped' | 'completed'
export type SettlementStatus = 'pending' | 'reconciled' | 'diff_found' | 'invoice_matched' | 'payment_requested' | 'completed'
export type InvoiceStatus = 'draft' | 'matched' | 'cancelled'
export type PaymentStatus = 'pending' | 'executing' | 'completed' | 'failed'
export type ReconcileDiffStatus = 'open' | 'repaired'

export interface Supplier {
  supplier_id: string
  supplier_code: string
  supplier_name: string
  supplier_type: SupplierType
  tax_id: string
  contact_name: string
  contact_phone: string
  contact_email: string
  status: SupplierStatus
  published_version: number
  governance_state: GovernanceState
}

export interface SupplierScope {
  scope_id: string
  supplier_id: string
  enterprise_sku_id: string
  agreement_price: number | null
  lead_time_days: number | null
  min_order_qty: number | null
  min_package_qty: number | null
  status: string
}

export interface Quotation {
  quotation_id: string
  supplier_id: string
  quotation_code: string
  status: QuotationStatus
  governance_state: GovernanceState
  valid_from: string | null
  valid_until: string | null
}

export interface SupplierEvaluation {
  evaluation_id: string
  supplier_id: string
  evaluation_period: string
  on_time_delivery_rate: number
  quality_pass_rate: number
  overall_score: number
  grade: SupplierGrade
  evaluated_at: string | null
}

export interface PurchaseRequest {
  request_id: string
  request_code: string
  title: string
  total_amount: number
  status: RequestStatus
  approved_by: string | null
  converted_order_id: string | null
  created_at: string | null
}

export interface PurchaseOrder {
  order_id: string
  order_code: string
  supplier_id: string
  warehouse_id: string | null
  total_amount: number
  status: OrderStatus
  approved_by: string | null
  sent_at: string | null
  created_at: string | null
}

export interface PurchaseOrderLine {
  line_id: string
  sku_id: string
  ordered_quantity: number
  received_quantity: number
  unit_price: number
  lead_time_days: number
  remark: string
}

export interface Asn {
  asn_id: string
  asn_code: string
  order_id: string
  supplier_id: string
  warehouse_id: string
  status: AsnStatus
}

export interface PurchaseReceipt {
  receipt_id: string
  receipt_code: string
  order_id: string
  supplier_id: string
  warehouse_id: string
  status: ReceiptStatus
  wms_receiving_id: string | null
  inv_transaction_ids: string[]
  confirmed_at: string | null
}

export interface PurchaseReturn {
  return_id: string
  return_code: string
  order_id: string
  supplier_id: string
  status: ReturnStatus
  inv_transaction_ids: string[]
  shipped_at: string | null
}

export interface PurchaseSettlement {
  settlement_id: string
  settlement_code: string
  order_id: string
  supplier_id: string
  total_amount: number
  received_amount: number
  diff_amount: number
  status: SettlementStatus
  reconciled_at: string | null
}

export interface Invoice {
  invoice_id: string
  invoice_code: string
  supplier_id: string
  settlement_id: string | null
  invoice_amount: number
  matched_amount: number
  status: InvoiceStatus
}

export interface PaymentRequest {
  payment_id: string
  payment_code: string
  settlement_id: string
  supplier_id: string
  amount: number
  status: PaymentStatus
  paid_at: string | null
}

export interface ReconcileDiff {
  diff_id: string
  order_id: string
  sku_id: string
  warehouse_id: string
  pur_quantity: number
  wms_quantity: number
  inv_quantity: number
  diff_type: string
  status: ReconcileDiffStatus
  created_at: string | null
}

export interface IdResult { [key: string]: string }

export interface CreateSupplierRequest {
  supplier_code: string
  supplier_name: string
  supplier_type?: SupplierType
  tax_id?: string
  contact_name?: string
  contact_phone?: string
  contact_email?: string
  address_province?: string
  address_city?: string
  address_district?: string
  address_detail?: string
  bank_name?: string
  account_number_masked?: string
  bank_branch?: string
}

export interface SupplierScopeRequest {
  enterprise_sku_id: string
  agreement_price?: number
  lead_time_days?: number
  min_order_qty?: number
  min_package_qty?: number
}

export interface CreateQuotationRequest {
  supplier_id: string
  quotation_code: string
  valid_from?: string
  valid_until?: string
  payment_terms?: string
  lines: { sku_id: string; unit_price: number; lead_time_days?: number; min_order_qty?: number }[]
}

export interface SupplierEvaluationRequest {
  evaluation_period: string
  on_time_delivery_rate: number
  quality_pass_rate: number
  response_speed_score?: number
}

export interface CreatePurchaseRequestRequest {
  request_code: string
  title?: string
  department_id?: string
  budget_id?: string
  lines: { sku_id: string; quantity: number; unit_price?: number; remark?: string }[]
}

export interface CreatePurchaseOrderRequest {
  order_code: string
  supplier_id: string
  warehouse_id?: string
  request_id?: string
  lines: { sku_id: string; ordered_quantity: number; unit_price: number; lead_time_days?: number; remark?: string }[]
}

export interface CreateAsnRequest {
  asn_code: string
  order_id: string
  supplier_id: string
  warehouse_id: string
  lines: { order_line_id: string; sku_id: string; expected_quantity: number }[]
}

export interface CreateReceiptRequest {
  receipt_code: string
  order_id: string
  asn_id?: string
  supplier_id: string
  warehouse_id: string
}

export interface ReceiptConfirmRequest {
  receiving_zone_id: string
  lines: {
    order_line_id: string
    sku_id: string
    received_quantity: number
    location_id: string
    lot_number?: string
    batch_number?: string
  }[]
  idempotency_key?: string
  correlation_id?: string
}

export interface CreatePurchaseReturnRequest {
  return_code: string
  order_id: string
  supplier_id: string
  warehouse_id?: string
  lines: { order_line_id: string; sku_id: string; return_quantity: number; reason?: string }[]
}

export interface CreateSettlementRequest {
  settlement_code: string
  order_id: string
  supplier_id: string
  total_amount: number
}

export interface CreateInvoiceRequest {
  invoice_code: string
  supplier_id: string
  settlement_id?: string
  invoice_amount: number
}

export interface ApproveRequest {
  approved: boolean
  opinion?: string
}