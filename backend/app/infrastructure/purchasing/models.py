"""PUR ORM 模型 - 所有 pur_* 表。企业级表含 tenant_id（租户隔离），复用 MDM Base。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, Index, UniqueConstraint,
    func, CheckConstraint, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.mdm.models import Base


class PurSupplierORM(Base):
    __tablename__ = "pur_supplier"
    __table_args__ = (
        UniqueConstraint("tenant_id", "supplier_code", name="uq_pur_supplier_code"),
        Index("idx_pur_supplier_tenant_status", "tenant_id", "status"),
    )
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    supplier_code: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(256), nullable=False)
    supplier_type: Mapped[str] = mapped_column(String(32), nullable=False, default="distributor")
    tax_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    contact_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    address_province: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    address_city: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    address_district: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    address_detail: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    bank_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    account_number_masked: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    bank_branch: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    published_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    governance_state: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurSupplierScopeORM(Base):
    __tablename__ = "pur_supplier_scope"
    __table_args__ = (
        UniqueConstraint("tenant_id", "supplier_id", "enterprise_sku_id", name="uq_pur_scope_sku"),
        Index("idx_pur_scope_supplier", "tenant_id", "supplier_id"),
    )
    scope_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_supplier.supplier_id"), nullable=False)
    enterprise_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    agreement_price: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_order_qty: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    min_package_qty: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurQuotationORM(Base):
    __tablename__ = "pur_quotation"
    __table_args__ = (
        UniqueConstraint("tenant_id", "quotation_code", name="uq_pur_quotation_code"),
        Index("idx_pur_quotation_supplier", "tenant_id", "supplier_id"),
    )
    quotation_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_supplier.supplier_id"), nullable=False)
    quotation_code: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    governance_state: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurQuotationLineORM(Base):
    __tablename__ = "pur_quotation_line"
    __table_args__ = (Index("idx_pur_qline_quotation", "tenant_id", "quotation_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quotation_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_quotation.quotation_id"), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    unit_price: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_order_qty: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurSupplierEvaluationORM(Base):
    __tablename__ = "pur_supplier_evaluation"
    __table_args__ = (Index("idx_pur_eval_supplier_period", "tenant_id", "supplier_id", "evaluation_period"),)
    evaluation_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_supplier.supplier_id"), nullable=False)
    evaluation_period: Mapped[str] = mapped_column(String(16), nullable=False)
    on_time_delivery_rate: Mapped[float] = mapped_column(NUMERIC(6, 4), nullable=False, default=0)
    quality_pass_rate: Mapped[float] = mapped_column(NUMERIC(6, 4), nullable=False, default=0)
    response_speed_score: Mapped[float | None] = mapped_column(NUMERIC(6, 2), nullable=True)
    overall_score: Mapped[float] = mapped_column(NUMERIC(6, 2), nullable=False, default=0)
    grade: Mapped[str] = mapped_column(String(16), nullable=False, default="unqualified")
    evaluated_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseRequestORM(Base):
    __tablename__ = "pur_purchase_request"
    __table_args__ = (
        UniqueConstraint("tenant_id", "request_code", name="uq_pur_request_code"),
        Index("idx_pur_request_tenant_status", "tenant_id", "status"),
    )
    request_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    request_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    department_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    budget_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    total_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    approved_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_order_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseRequestLineORM(Base):
    __tablename__ = "pur_purchase_request_line"
    __table_args__ = (Index("idx_pur_reqline_request", "tenant_id", "request_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    request_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_purchase_request.request_id"), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    unit_price: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    remark: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseOrderORM(Base):
    __tablename__ = "pur_purchase_order"
    __table_args__ = (
        UniqueConstraint("tenant_id", "order_code", name="uq_pur_order_code"),
        Index("idx_pur_order_tenant_status", "tenant_id", "status"),
        Index("idx_pur_order_supplier", "tenant_id", "supplier_id"),
    )
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    order_code: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_supplier.supplier_id"), nullable=False)
    warehouse_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    request_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    total_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    approved_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseOrderLineORM(Base):
    __tablename__ = "pur_purchase_order_line"
    __table_args__ = (Index("idx_pur_orderline_order", "tenant_id", "order_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_purchase_order.order_id"), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    ordered_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    received_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    unit_price: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remark: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurAsnORM(Base):
    __tablename__ = "pur_asn"
    __table_args__ = (
        UniqueConstraint("tenant_id", "asn_code", name="uq_pur_asn_code"),
        Index("idx_pur_asn_order", "tenant_id", "order_id"),
    )
    asn_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    asn_code: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_purchase_order.order_id"), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurAsnLineORM(Base):
    __tablename__ = "pur_asn_line"
    __table_args__ = (Index("idx_pur_asnline_asn", "tenant_id", "asn_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    asn_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_asn.asn_id"), nullable=False)
    order_line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    expected_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseReceiptORM(Base):
    __tablename__ = "pur_purchase_receipt"
    __table_args__ = (
        UniqueConstraint("tenant_id", "receipt_code", name="uq_pur_receipt_code"),
        Index("idx_pur_receipt_order", "tenant_id", "order_id"),
    )
    receipt_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    receipt_code: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_purchase_order.order_id"), nullable=False)
    asn_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    wms_receiving_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseReceiptLineORM(Base):
    __tablename__ = "pur_purchase_receipt_line"
    __table_args__ = (Index("idx_pur_recline_receipt", "tenant_id", "receipt_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    receipt_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_purchase_receipt.receipt_id"), nullable=False)
    order_line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    received_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    qc_result: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    wms_receiving_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseReturnORM(Base):
    __tablename__ = "pur_purchase_return"
    __table_args__ = (
        UniqueConstraint("tenant_id", "return_code", name="uq_pur_return_code"),
        Index("idx_pur_return_order", "tenant_id", "order_id"),
    )
    return_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    return_code: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_purchase_order.order_id"), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    approved_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseReturnLineORM(Base):
    __tablename__ = "pur_purchase_return_line"
    __table_args__ = (Index("idx_pur_retline_return", "tenant_id", "return_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    return_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_purchase_return.return_id"), nullable=False)
    order_line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    return_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseSettlementORM(Base):
    __tablename__ = "pur_purchase_settlement"
    __table_args__ = (
        UniqueConstraint("tenant_id", "settlement_code", name="uq_pur_settlement_code"),
        Index("idx_pur_settlement_order", "tenant_id", "order_id"),
    )
    settlement_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    settlement_code: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("pur_purchase_order.order_id"), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    total_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    received_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    diff_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurInvoiceORM(Base):
    __tablename__ = "pur_invoice"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_code", name="uq_pur_invoice_code"),
        Index("idx_pur_invoice_supplier", "tenant_id", "supplier_id"),
    )
    invoice_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    invoice_code: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    settlement_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    invoice_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    matched_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPaymentRequestORM(Base):
    __tablename__ = "pur_payment_request"
    __table_args__ = (
        UniqueConstraint("tenant_id", "payment_code", name="uq_pur_payment_code"),
        Index("idx_pur_payment_settlement", "tenant_id", "settlement_id"),
    )
    payment_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    payment_code: Mapped[str] = mapped_column(String(64), nullable=False)
    settlement_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurPurchaseAuditORM(Base):
    __tablename__ = "pur_purchase_audit"
    __table_args__ = (Index("idx_pur_audit_tenant_event", "tenant_id", "event_type"),)
    audit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    order_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    receipt_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    return_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    settlement_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    before_state: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    after_state: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    wms_receiving_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    operated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurReconcileDiffORM(Base):
    __tablename__ = "pur_reconcile_diff"
    __table_args__ = (Index("idx_pur_reconcile_diff_order", "tenant_id", "order_id"),)
    diff_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    pur_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    wms_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    inv_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    diff_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())