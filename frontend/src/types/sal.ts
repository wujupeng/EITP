export type CustomerType = 'individual' | 'enterprise' | 'government' | 'partner'
export type CustomerStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'active' | 'disabled'
export type CategoryStatus = 'active' | 'disabled'
export type GovernanceState = 'draft' | 'submitted' | 'approved' | 'rejected' | 'published'
export type OverCreditStrategy = 'block' | 'warn' | 'special_approval'
export type PriceType = 'agreement' | 'discount' | 'promotion' | 'standard'
export type QuotationStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'converted' | 'expired' | 'cancelled'
export type SalesOrderStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'reserved' | 'partial_shipped' | 'shipped' | 'completed' | 'cancelled' | 'closed'
export type SalesOrderLineStatus = 'open' | 'reserved' | 'partial_shipped' | 'shipped' | 'closed' | 'cancelled'
export type ShipmentStatus = 'draft' | 'picking' | 'packed' | 'shipped' | 'cancelled' | 'failed'
export type PackingStatus = 'pending' | 'completed'
export type SalesReturnStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'receiving' | 'qc' | 'disposed' | 'completed' | 'cancelled'
export type QcResult = 'pending' | 'passed' | 'failed' | 'conditional'
export type Disposition = 'restock' | 'scrap' | 'return_to_supplier' | 'rework'
export type SettlementStatus = 'pending' | 'reconciled' | 'diff_found' | 'invoice_matched' | 'payment_requested' | 'payment_completed' | 'failed'
export type InvoiceStatus = 'draft' | 'matched' | 'cancelled'
export type PaymentStatus = 'pending' | 'executing' | 'completed' | 'failed'
export type PaymentMethod = 'bank_transfer' | 'cheque' | 'cash' | 'credit_card' | 'electronic'
export type PickingStrategy = 'fifo' | 'fefo' | 'by_location' | 'by_batch'
export type ReconcileDiffStatus = 'open' | 'repaired'

export interface Customer {
  customer_id: string
  customer_code: string
  customer_name: string
  customer_type: CustomerType
  tax_id: string
  contact_name: string
  contact_phone: string
  contact_email: string
  status: CustomerStatus
  published_version: number
  governance_state: GovernanceState
  category_ids: string[]
}

export interface CustomerCategory {
  category_id: string
  category_code: string
  category_name: string
  description: string
  status: CategoryStatus
}

export interface CreditLimit {
  credit_limit_id: string
  customer_id: string
  total_limit: number
  used_amount: number
  available_amount: number
  credit_period_days: number
  over_credit_strategy: OverCreditStrategy
}

export interface CustomerPricing {
  pricing_id: string
  customer_id: string
  category_id: string | null
  enterprise_sku_id: string
  price_type: PriceType
  agreement_price: number | null
  discount_rate: number | null
  priority: number
  valid_from: string | null
  valid_until: string | null
  governance_state: GovernanceState
}

export interface SalesQuotation {
  quotation_id: string
  quotation_code: string
  customer_id: string
  status: QuotationStatus
  governance_state: GovernanceState
  valid_from: string | null
  valid_until: string | null
  payment_terms: string
  currency: string
  converted_order_id: string | null
  created_at: string | null
}

export interface SalesOrder {
  order_id: string
  order_code: string
  customer_id: string
  shipping_warehouse_id: string | null
  source_quotation_id: string | null
  payment_terms: string
  currency: string
  total_amount: number
  status: SalesOrderStatus
  approved_by: string | null
  reservation_ids: string[]
  created_at: string | null
}

export interface SalesOrderLine {
  line_id: string
  order_id: string
  enterprise_sku_id: string
  ordered_quantity: number
  reserved_quantity: number
  shipped_quantity: number
  remaining_quantity: number
  unit_price: number
  expected_delivery_date: string | null
  line_status: SalesOrderLineStatus
}

export interface ShipmentOrder {
  shipment_id: string
  shipment_code: string
  order_id: string
  customer_id: string
  shipping_warehouse_id: string
  status: ShipmentStatus
  picking_strategy: PickingStrategy
  wms_picking_id: string | null
  wms_shipping_id: string | null
  inv_transaction_ids: string[]
  logistics_tracking_no: string | null
  shipped_at: string | null
}

export interface PackingRecord {
  packing_id: string
  shipment_id: string
  packing_code: string
  status: PackingStatus
  package_count: number
  total_gross_weight: number
  total_net_weight: number
  completed_at: string | null
}

export interface SalesReturn {
  return_id: string
  return_code: string
  order_id: string
  customer_id: string
  warehouse_id: string | null
  status: SalesReturnStatus
  wms_receiving_id: string | null
  inv_transaction_ids: string[]
  qc_result: QcResult
  disposition: Disposition | null
  completed_at: string | null
}

export interface SalesSettlement {
  settlement_id: string
  settlement_code: string
  order_id: string
  customer_id: string
  total_amount: number
  shipped_amount: number
  diff_amount: number
  status: SettlementStatus
  revenue_landed: boolean
  reconciled_at: string | null
}

export interface SalesInvoice {
  invoice_id: string
  invoice_code: string
  customer_id: string
  settlement_id: string | null
  invoice_amount: number
  tax_amount: number
  matched_amount: number
  status: InvoiceStatus
}

export interface PaymentReceipt {
  payment_id: string
  payment_code: string
  settlement_id: string
  customer_id: string
  amount: number
  payment_method: PaymentMethod
  status: PaymentStatus
  paid_at: string | null
}

export interface ReconcileDiff {
  diff_id: string
  order_id: string
  sku_id: string
  warehouse_id: string
  sal_quantity: number
  wms_quantity: number
  inv_quantity: number
  diff_type: string
  status: ReconcileDiffStatus
  created_at: string | null
}

export interface IdResult { [key: string]: string }

export interface CreateCustomerRequest {
  customer_code: string
  customer_name: string
  customer_type?: CustomerType
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
  category_ids?: string[]
}

export interface CreateCustomerCategoryRequest {
  category_code: string
  category_name: string
  description?: string
}

export interface SetCreditLimitRequest {
  total_limit: number
  credit_period_days: number
  over_credit_strategy: OverCreditStrategy
}

export interface SetCustomerPricingRequest {
  category_id?: string
  enterprise_sku_id: string
  price_type: PriceType
  agreement_price?: number
  discount_rate?: number
  priority?: number
  valid_from?: string
  valid_until?: string
}

export interface CreateSalesQuotationRequest {
  quotation_code: string
  customer_id: string
  valid_from?: string
  valid_until?: string
  payment_terms?: string
  currency?: string
  lines: { enterprise_sku_id: string; unit_price: number; quantity?: number }[]
}

export interface CreateSalesOrderRequest {
  order_code: string
  customer_id: string
  shipping_warehouse_id?: string
  source_quotation_id?: string
  payment_terms?: string
  currency?: string
  lines: {
    enterprise_sku_id: string
    ordered_quantity: number
    unit_price: number
    expected_delivery_date?: string
  }[]
}

export interface ChangeSalesOrderRequest {
  reason: string
  lines: { line_id: string; ordered_quantity: number; unit_price?: number }[]
}

export interface CreateShipmentRequest {
  shipment_code: string
  order_id: string
  customer_id: string
  shipping_warehouse_id: string
  picking_strategy?: PickingStrategy
  lines: { order_line_id: string; enterprise_sku_id: string; ship_quantity: number }[]
}

export interface ShipmentConfirmRequest {
  logistics_tracking_no?: string
  idempotency_key?: string
  correlation_id?: string
}

export interface CreatePackingRequest {
  shipment_id: string
  packing_code: string
  package_count: number
  total_gross_weight: number
  total_net_weight: number
  details?: { sku_id: string; quantity: number; package_no: string }[]
}

export interface CreateSalesReturnRequest {
  return_code: string
  order_id: string
  customer_id: string
  warehouse_id?: string
  lines: { order_line_id: string; enterprise_sku_id: string; return_quantity: number; reason?: string }[]
}

export interface ReturnQcRequest {
  line_id: string
  qc_result: QcResult
  qc_note?: string
}

export interface ReturnDisposeRequest {
  disposition: Disposition
  note?: string
}

export interface CreateSalesSettlementRequest {
  settlement_code: string
  order_id: string
  customer_id: string
  total_amount: number
}

export interface SettlementReconcileRequest {
  shipped_amount: number
  idempotency_key?: string
}

export interface MatchInvoiceRequest {
  invoice_id: string
  matched_amount: number
}

export interface RequestPaymentRequest {
  payment_code: string
  amount: number
  payment_method: PaymentMethod
}

export interface CreateSalesInvoiceRequest {
  invoice_code: string
  customer_id: string
  settlement_id?: string
  invoice_amount: number
  tax_amount?: number
}

export interface InvoiceMatchRequest {
  settlement_id: string
  matched_amount: number
}

export interface PaymentConfirmRequest {
  paid: boolean
  paid_at?: string
}

export interface ApproveRequest {
  approved: boolean
  opinion?: string
}