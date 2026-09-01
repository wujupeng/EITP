"""SAL Pydantic v2 Schema - 所有 SAL 接口请求/响应模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ────────────────────────────── 通用 ──────────────────────────────


class ApproveRequest(BaseModel):
    approved: bool = True
    opinion: str = Field("", max_length=512)


class ConvertRequest(BaseModel):
    order_code: str = Field(..., max_length=64)


class IdempotencyRequest(BaseModel):
    idempotency_key: str = Field("", max_length=128)


# ────────────────────────────── 客户主数据 ──────────────────────────────


class ContactInfoSchema(BaseModel):
    name: str = Field("", max_length=128)
    phone: str = Field("", max_length=32)
    email: str = Field("", max_length=128)


class AddressSchema(BaseModel):
    address_type: str = Field("shipping", pattern="^(default|shipping|billing)$")
    is_default: bool = False
    is_shipping: bool = False
    is_billing: bool = False
    province: str = Field("", max_length=64)
    city: str = Field("", max_length=64)
    district: str = Field("", max_length=64)
    detail: str = Field("", max_length=256)
    receiver_name: str = Field("", max_length=128)
    receiver_phone: str = Field("", max_length=32)


class BankAccountSchema(BaseModel):
    bank_name: str = Field("", max_length=128)
    account_number_masked: str = Field("", max_length=64)
    bank_branch: str = Field("", max_length=128)


class CreateCustomerRequest(BaseModel):
    customer_code: str = Field(..., max_length=64)
    customer_name: str = Field(..., max_length=256)
    customer_type: str = Field("corporate", pattern="^(corporate|individual|government|partner)$")
    tax_id: str = Field("", max_length=64)
    contact_info: ContactInfoSchema = Field(default_factory=ContactInfoSchema)
    bank_account: BankAccountSchema = Field(default_factory=BankAccountSchema)


class UpdateCustomerRequest(BaseModel):
    customer_name: str | None = Field(None, max_length=256)
    tax_id: str | None = Field(None, max_length=64)
    contact_info: ContactInfoSchema | None = None
    bank_account: BankAccountSchema | None = None


class CustomerResponse(BaseModel):
    customer_id: str
    customer_code: str
    customer_name: str
    customer_type: str
    status: str
    published_version: int
    governance_state: str
    created_at: str | None = None


class CreateCategoryRequest(BaseModel):
    category_code: str = Field(..., max_length=64)
    category_name: str = Field(..., max_length=256)
    description: str = Field("", max_length=512)


class CategoryResponse(BaseModel):
    category_id: str
    category_code: str
    category_name: str
    status: str


class CreditLimitRequest(BaseModel):
    total_limit: float = Field(..., ge=0)
    credit_period_days: int = Field(30, ge=0)
    over_credit_strategy: str = Field("block", pattern="^(block|warn|special_approval)$")


class CreditLimitResponse(BaseModel):
    credit_limit_id: str
    customer_id: str
    total_limit: float
    used_amount: float
    available_amount: float
    credit_period_days: int
    over_credit_strategy: str
    version: int


class CustomerPricingRequest(BaseModel):
    customer_id: UUID | None = None
    category_id: UUID | None = None
    enterprise_sku_id: UUID
    price_type: str = Field("standard", pattern="^(standard|agreement|discount|promotion)$")
    agreement_price: float | None = Field(None, ge=0)
    discount_rate: float | None = Field(None, ge=0, le=1)
    priority: int = Field(4, ge=1, le=10)
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class CustomerPricingResponse(BaseModel):
    pricing_id: str
    customer_id: str | None = None
    category_id: str | None = None
    enterprise_sku_id: str
    price_type: str
    agreement_price: float | None = None
    discount_rate: float | None = None
    priority: int
    status: str


# ────────────────────────────── 销售报价 ──────────────────────────────


class QuotationLineRequest(BaseModel):
    enterprise_sku_id: UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    expected_delivery_date: datetime | None = None


class CreateSalesQuotationRequest(BaseModel):
    quotation_code: str = Field(..., max_length=64)
    customer_id: UUID
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    payment_terms: str = Field("", max_length=256)
    currency: str = Field("CNY", max_length=16)
    lines: list[QuotationLineRequest] = []


class SalesQuotationResponse(BaseModel):
    quotation_id: str
    quotation_code: str
    customer_id: str
    status: str
    governance_state: str
    valid_from: str | None = None
    valid_until: str | None = None
    converted_order_id: str | None = None


# ────────────────────────────── 销售订单 ──────────────────────────────


class SalesOrderLineRequest(BaseModel):
    enterprise_sku_id: UUID
    ordered_quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    expected_delivery_date: datetime | None = None


class CreateSalesOrderRequest(BaseModel):
    order_code: str = Field(..., max_length=64)
    customer_id: UUID
    shipping_warehouse_id: UUID | None = None
    source_quotation_id: UUID | None = None
    payment_terms: str = Field("", max_length=256)
    currency: str = Field("CNY", max_length=16)
    lines: list[SalesOrderLineRequest] = []
    idempotency_key: str = Field("", max_length=128)


class UpdateSalesOrderRequest(BaseModel):
    shipping_warehouse_id: UUID | None = None
    payment_terms: str | None = Field(None, max_length=256)


class ChangeOrderRequest(BaseModel):
    reason: str = Field("", max_length=512)
    lines: list[SalesOrderLineRequest] = []


class FourStateQtyResponse(BaseModel):
    line_id: str
    enterprise_sku_id: str
    ordered_quantity: float
    reserved_quantity: float
    shipped_quantity: float
    remaining_quantity: float
    status: str


class SalesOrderResponse(BaseModel):
    order_id: str
    order_code: str
    customer_id: str
    shipping_warehouse_id: str | None = None
    total_amount: float
    status: str
    version: int
    reservation_ids: list[str] = []
    created_at: str | None = None


# ────────────────────────────── 发货与包装 ──────────────────────────────


class ShipmentLineRequest(BaseModel):
    order_line_id: UUID
    enterprise_sku_id: UUID
    ship_quantity: float = Field(..., gt=0)


class CreateShipmentRequest(BaseModel):
    shipment_code: str = Field(..., max_length=64)
    order_ids: list[UUID] = []
    shipping_warehouse_id: UUID
    picking_strategy: str = Field("fifo", pattern="^(fifo|fefo|by_location|by_batch)$")
    lines: list[ShipmentLineRequest] = []
    idempotency_key: str = Field("", max_length=128)


class ShipmentConfirmRequest(BaseModel):
    logistics_no: str = Field(..., max_length=128)
    carrier: str | None = Field(None, max_length=128)
    idempotency_key: str = Field(..., max_length=128)


class ShipmentResponse(BaseModel):
    shipment_id: str
    shipment_code: str
    order_ids: list[str] = []
    shipping_warehouse_id: str
    status: str
    wms_picking_task_id: str | None = None
    wms_shipping_id: str | None = None
    inv_transaction_ids: list[str] = []
    logistics_no: str | None = None
    shipped_at: str | None = None


class PackingLineRequest(BaseModel):
    shipment_line_id: UUID
    carton_no: str = Field("", max_length=64)
    packed_quantity: float = Field(..., gt=0)
    gross_weight: float = Field(0, ge=0)
    net_weight: float = Field(0, ge=0)
    volume: float = Field(0, ge=0)


class CreatePackingRequest(BaseModel):
    package_count: int = Field(0, ge=0)
    total_gross_weight: float = Field(0, ge=0)
    total_net_weight: float = Field(0, ge=0)
    total_volume: float = Field(0, ge=0)
    lines: list[PackingLineRequest] = []


class PackingResponse(BaseModel):
    packing_id: str
    shipment_id: str
    package_count: int
    total_gross_weight: float
    total_net_weight: float
    total_volume: float
    status: str
    packed_at: str | None = None


# ────────────────────────────── 销售退货 ──────────────────────────────


class ReturnLineRequest(BaseModel):
    order_line_id: UUID
    enterprise_sku_id: UUID
    return_quantity: float = Field(..., gt=0)
    refund_amount: float = Field(0, ge=0)
    shipment_line_id: UUID | None = None


class CreateSalesReturnRequest(BaseModel):
    return_code: str = Field(..., max_length=64)
    order_id: UUID
    original_shipment_id: UUID
    return_reason: str = Field("", max_length=512)
    lines: list[ReturnLineRequest] = []
    idempotency_key: str = Field("", max_length=128)


class ReturnReceiveRequest(BaseModel):
    idempotency_key: str = Field("", max_length=128)


class QcResultRequest(BaseModel):
    line_id: UUID
    qc_result: str = Field(..., pattern="^(passed|failed|conditional|pending)$")
    qc_note: str = Field("", max_length=512)


class DispositionRequest(BaseModel):
    line_id: UUID
    disposition: str = Field(..., pattern="^(restock|quarantine|scrap)$")


class SalesReturnResponse(BaseModel):
    return_id: str
    return_code: str
    order_id: str
    original_shipment_id: str
    status: str
    refund_amount: float
    wms_receiving_id: str | None = None
    inv_transaction_ids: list[str] = []


# ────────────────────────────── 销售结算 ──────────────────────────────


class CreateSettlementRequest(BaseModel):
    settlement_code: str = Field(..., max_length=64)
    order_id: UUID
    receivable_amount: float = Field(..., ge=0)
    idempotency_key: str = Field("", max_length=128)


class ReconcileRequest(BaseModel):
    received_amount: float = Field(..., ge=0)
    diff_threshold: float = Field(0.01, ge=0)


class MatchInvoiceRequest(BaseModel):
    invoice_id: UUID
    matched_amount: float = Field(..., ge=0)
    diff_threshold: float = Field(0.01, ge=0)


class RequestPaymentRequest(BaseModel):
    payment_code: str = Field(..., max_length=64)
    amount: float = Field(..., ge=0)


class SettlementResponse(BaseModel):
    settlement_id: str
    settlement_code: str
    order_id: str
    receivable_amount: float
    refund_amount: float
    net_receivable_amount: float
    status: str
    invoice_id: str | None = None
    payment_receipt_id: str | None = None
    revenue_landed: bool
    reconciled_at: str | None = None


class LandRevenueRequest(BaseModel):
    sku_id: UUID
    warehouse_id: UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    moving_avg_cost: float = Field(0, ge=0)
    idempotency_key: str = Field("", max_length=128)


# ────────────────────────────── 发票 ──────────────────────────────


class InvoiceLineRequest(BaseModel):
    enterprise_sku_id: UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    tax_rate: float = Field(0, ge=0, le=1)


class CreateInvoiceRequest(BaseModel):
    invoice_code: str = Field(..., max_length=64)
    customer_id: UUID
    invoice_amount: float = Field(..., ge=0)
    tax_amount: float = Field(0, ge=0)
    lines: list[InvoiceLineRequest] = []


class InvoiceMatchRequest(BaseModel):
    settlement_id: UUID
    matched_amount: float = Field(..., ge=0)
    diff_threshold: float = Field(0.01, ge=0)


class InvoiceResponse(BaseModel):
    invoice_id: str
    invoice_code: str
    customer_id: str
    invoice_amount: float
    tax_amount: float
    status: str
    matched_settlement_id: str | None = None


# ────────────────────────────── 收款 ──────────────────────────────


class PaymentConfirmRequest(BaseModel):
    payment_no: str = Field("", max_length=128)
    idempotency_key: str = Field("", max_length=128)


class PaymentResponse(BaseModel):
    payment_receipt_id: str
    settlement_id: str
    payment_amount: float
    payment_method: str
    status: str
    payment_no: str | None = None
    completed_at: str | None = None


# ────────────────────────────── 对账 ──────────────────────────────


class ReconcileRunRequest(BaseModel):
    order_id: UUID | None = None


class ReconcileRepairRequest(BaseModel):
    shipment_id: UUID
    repair_note: str = Field("", max_length=512)


class SalReconcileDiffResponse(BaseModel):
    audit_id: str
    event_type: str
    order_id: str | None = None
    shipment_id: str | None = None
    wms_shipping_id: str | None = None
