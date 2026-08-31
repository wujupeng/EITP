"""PUR Pydantic v2 Schema - 所有 PUR 接口请求/响应模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSupplierRequest(BaseModel):
    supplier_code: str = Field(..., max_length=64)
    supplier_name: str = Field(..., max_length=256)
    supplier_type: str = Field("distributor", pattern="^(distributor|manufacturer|agent|individual)$")
    tax_id: str = Field("", max_length=64)
    contact_name: str = Field("", max_length=128)
    contact_phone: str = Field("", max_length=32)
    contact_email: str = Field("", max_length=128)
    address_province: str = Field("", max_length=64)
    address_city: str = Field("", max_length=64)
    address_district: str = Field("", max_length=64)
    address_detail: str = Field("", max_length=256)
    bank_name: str = Field("", max_length=128)
    account_number_masked: str = Field("", max_length=64)
    bank_branch: str = Field("", max_length=128)


class PatchSupplierRequest(BaseModel):
    supplier_name: str | None = Field(None, max_length=256)
    contact_name: str | None = Field(None, max_length=128)
    contact_phone: str | None = Field(None, max_length=32)
    contact_email: str | None = Field(None, max_length=128)
    address_province: str | None = Field(None, max_length=64)
    address_city: str | None = Field(None, max_length=64)
    address_district: str | None = Field(None, max_length=64)
    address_detail: str | None = Field(None, max_length=256)
    bank_name: str | None = Field(None, max_length=128)
    account_number_masked: str | None = Field(None, max_length=64)
    bank_branch: str | None = Field(None, max_length=128)


class SupplierScopeRequest(BaseModel):
    enterprise_sku_id: UUID
    agreement_price: float | None = Field(None, ge=0)
    lead_time_days: int | None = Field(None, ge=0)
    min_order_qty: float | None = Field(None, ge=0)
    min_package_qty: float | None = Field(None, ge=0)


class ApproveRequest(BaseModel):
    approved: bool = True
    opinion: str = Field("", max_length=512)


class SupplierResponse(BaseModel):
    supplier_id: str
    supplier_code: str
    supplier_name: str
    supplier_type: str
    status: str
    published_version: int
    governance_state: str
    created_at: str | None = None


class SupplierScopeResponse(BaseModel):
    scope_id: str
    supplier_id: str
    enterprise_sku_id: str
    agreement_price: float | None = None
    lead_time_days: int | None = None
    min_order_qty: float | None = None
    min_package_qty: float | None = None
    status: str


class QuotationLineRequest(BaseModel):
    sku_id: UUID
    unit_price: float = Field(..., ge=0)
    lead_time_days: int = Field(0, ge=0)
    min_order_qty: float = Field(1, ge=0)


class CreateQuotationRequest(BaseModel):
    supplier_id: UUID
    quotation_code: str = Field(..., max_length=64)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    payment_terms: str = Field("", max_length=256)
    lines: list[QuotationLineRequest] = []


class QuotationResponse(BaseModel):
    quotation_id: str
    supplier_id: str
    quotation_code: str
    status: str
    governance_state: str
    valid_from: str | None = None
    valid_until: str | None = None


class SupplierEvaluationRequest(BaseModel):
    evaluation_period: str = Field(..., pattern="^\\d{4}-[Q1-4]|\\d{4}-\\d{2}$")
    on_time_delivery_rate: float = Field(0, ge=0, le=1)
    quality_pass_rate: float = Field(0, ge=0, le=1)
    response_speed_score: float | None = Field(None, ge=0, le=100)


class SupplierEvaluationResponse(BaseModel):
    evaluation_id: str
    supplier_id: str
    evaluation_period: str
    on_time_delivery_rate: float
    quality_pass_rate: float
    overall_score: float
    grade: str
    evaluated_at: str | None = None


class PurchaseRequestLineRequest(BaseModel):
    sku_id: UUID
    quantity: float = Field(..., gt=0)
    unit_price: float | None = Field(None, ge=0)
    remark: str = Field("", max_length=512)


class CreatePurchaseRequestRequest(BaseModel):
    request_code: str = Field(..., max_length=64)
    title: str = Field("", max_length=256)
    department_id: UUID | None = None
    budget_id: UUID | None = None
    lines: list[PurchaseRequestLineRequest] = []


class PurchaseRequestResponse(BaseModel):
    request_id: str
    request_code: str
    title: str
    total_amount: float
    status: str
    approved_by: str | None = None
    converted_order_id: str | None = None
    created_at: str | None = None


class PurchaseOrderLineRequest(BaseModel):
    sku_id: UUID
    ordered_quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    lead_time_days: int = Field(0, ge=0)
    remark: str = Field("", max_length=512)


class CreatePurchaseOrderRequest(BaseModel):
    order_code: str = Field(..., max_length=64)
    supplier_id: UUID
    warehouse_id: UUID | None = None
    request_id: UUID | None = None
    lines: list[PurchaseOrderLineRequest] = []


class PatchPurchaseOrderRequest(BaseModel):
    warehouse_id: UUID | None = None
    lines: list[PurchaseOrderLineRequest] | None = None


class PurchaseOrderResponse(BaseModel):
    order_id: str
    order_code: str
    supplier_id: str
    warehouse_id: str | None = None
    total_amount: float
    status: str
    approved_by: str | None = None
    sent_at: str | None = None
    created_at: str | None = None


class ChangeOrderRequest(BaseModel):
    reason: str = Field("", max_length=512)
    lines: list[PurchaseOrderLineRequest] = []


class CreateAsnRequest(BaseModel):
    asn_code: str = Field(..., max_length=64)
    order_id: UUID
    supplier_id: UUID
    warehouse_id: UUID
    lines: list[dict] = []


class AsnArriveRequest(BaseModel):
    arrived: bool = True


class CreateReceiptRequest(BaseModel):
    receipt_code: str = Field(..., max_length=64)
    order_id: UUID
    asn_id: UUID | None = None
    supplier_id: UUID
    warehouse_id: UUID


class ReceiptConfirmLine(BaseModel):
    order_line_id: UUID
    sku_id: UUID
    received_quantity: float = Field(..., gt=0)
    location_id: UUID
    lot_number: str | None = None
    batch_number: str | None = None
    serial_numbers: list[str] = []


class ReceiptConfirmRequest(BaseModel):
    receiving_zone_id: UUID
    lines: list[ReceiptConfirmLine] = []
    idempotency_key: str | None = None
    correlation_id: str | None = None


class QcResultRequest(BaseModel):
    line_id: UUID
    qc_result: str = Field(..., pattern="^(passed|failed|conditional|pending)$")
    qc_note: str = Field("", max_length=512)


class ReceiptResponse(BaseModel):
    receipt_id: str
    receipt_code: str
    order_id: str
    supplier_id: str
    warehouse_id: str
    status: str
    wms_receiving_id: str | None = None
    inv_transaction_ids: list[str] = []
    confirmed_at: str | None = None


class PurchaseReturnLineRequest(BaseModel):
    order_line_id: UUID
    sku_id: UUID
    return_quantity: float = Field(..., gt=0)
    reason: str = Field("", max_length=512)


class CreatePurchaseReturnRequest(BaseModel):
    return_code: str = Field(..., max_length=64)
    order_id: UUID
    supplier_id: UUID
    warehouse_id: UUID | None = None
    lines: list[PurchaseReturnLineRequest] = []


class ReturnShipRequest(BaseModel):
    via_wms_shipping: bool = False
    idempotency_key: str | None = None


class PurchaseReturnResponse(BaseModel):
    return_id: str
    return_code: str
    order_id: str
    supplier_id: str
    status: str
    inv_transaction_ids: list[str] = []
    shipped_at: str | None = None


class CreateSettlementRequest(BaseModel):
    settlement_code: str = Field(..., max_length=64)
    order_id: UUID
    supplier_id: UUID
    total_amount: float = Field(..., ge=0)


class ReconcileRequest(BaseModel):
    received_amount: float = Field(..., ge=0)


class MatchInvoiceRequest(BaseModel):
    invoice_id: UUID
    matched_amount: float = Field(..., ge=0)


class RequestPaymentRequest(BaseModel):
    payment_code: str = Field(..., max_length=64)
    amount: float = Field(..., ge=0)


class SettlementResponse(BaseModel):
    settlement_id: str
    settlement_code: str
    order_id: str
    supplier_id: str
    total_amount: float
    received_amount: float
    diff_amount: float
    status: str
    reconciled_at: str | None = None


class CreateInvoiceRequest(BaseModel):
    invoice_code: str = Field(..., max_length=64)
    supplier_id: UUID
    settlement_id: UUID | None = None
    invoice_amount: float = Field(..., ge=0)
    lines: list[dict] = []


class InvoiceResponse(BaseModel):
    invoice_id: str
    invoice_code: str
    supplier_id: str
    settlement_id: str | None = None
    invoice_amount: float
    matched_amount: float
    status: str


class InvoiceMatchRequest(BaseModel):
    settlement_id: UUID
    matched_amount: float = Field(..., ge=0)


class PaymentConfirmRequest(BaseModel):
    paid: bool = True


class PaymentResponse(BaseModel):
    payment_id: str
    payment_code: str
    settlement_id: str
    supplier_id: str
    amount: float
    status: str
    paid_at: str | None = None


class ReconcileRunRequest(BaseModel):
    order_id: UUID


class ReconcileRepairRequest(BaseModel):
    diff_id: UUID
    repair_note: str = Field("", max_length=512)


class PurchaseReconcileDiffResponse(BaseModel):
    diff_id: str
    order_id: str
    sku_id: str
    warehouse_id: str
    pur_quantity: float
    wms_quantity: float
    inv_quantity: float
    diff_type: str
    status: str
    created_at: str | None = None
