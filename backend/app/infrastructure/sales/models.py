"""SAL ORM 模型 - 所有 sal_* 表。企业级表含 tenant_id（租户隔离），复用 MDM Base。

表清单（22 张）：
  sal_customer / sal_customer_address / sal_customer_contact / sal_customer_category
  sal_credit_limit / sal_customer_pricing
  sal_sales_quotation / sal_sales_quotation_line
  sal_sales_order / sal_sales_order_line
  sal_shipment_order / sal_shipment_line / sal_packing_record / sal_packing_line
  sal_sales_return / sal_return_line
  sal_sales_settlement / sal_settlement_reconcile_line
  sal_sales_invoice / sal_invoice_line / sal_payment_receipt
  sal_sales_audit

status 列统一 VARCHAR(32)（参考 PUR-001 迁移 038 扩容修复）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, Index, UniqueConstraint,
    func, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.mdm.models import Base


# ────────────────────────────── 客户主数据 ──────────────────────────────


class SalCustomerORM(Base):
    __tablename__ = "sal_customer"
    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_code", name="uq_sal_customer_code"),
        Index("idx_sal_customer_tenant_status", "tenant_id", "status"),
    )
    customer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    customer_code: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(256), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(32), nullable=False, default="corporate")
    tax_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    contact_info: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    bank_account: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    published_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    governance_state: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalCustomerAddressORM(Base):
    __tablename__ = "sal_customer_address"
    __table_args__ = (Index("idx_sal_cust_addr_customer", "tenant_id", "customer_id"),)
    address_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_customer.customer_id"), nullable=False)
    address_type: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_shipping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_billing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    province: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    district: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    detail: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    receiver_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    receiver_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalCustomerContactORM(Base):
    __tablename__ = "sal_customer_contact"
    __table_args__ = (Index("idx_sal_cust_contact_customer", "tenant_id", "customer_id"),)
    contact_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_customer.customer_id"), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    position: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalCustomerCategoryORM(Base):
    __tablename__ = "sal_customer_category"
    __table_args__ = (
        UniqueConstraint("tenant_id", "category_code", name="uq_sal_category_code"),
        Index("idx_sal_category_tenant_status", "tenant_id", "status"),
    )
    category_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    category_code: Mapped[str] = mapped_column(String(64), nullable=False)
    category_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalCreditLimitORM(Base):
    __tablename__ = "sal_credit_limit"
    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_id", name="uq_sal_credit_limit_customer"),
        Index("idx_sal_credit_limit_customer", "tenant_id", "customer_id"),
    )
    credit_limit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_customer.customer_id"), nullable=False)
    total_limit: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    used_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    credit_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    over_credit_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="block")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalCustomerPricingORM(Base):
    __tablename__ = "sal_customer_pricing"
    __table_args__ = (
        Index("idx_sal_pricing_customer", "tenant_id", "customer_id"),
        Index("idx_sal_pricing_category", "tenant_id", "category_id"),
        Index("idx_sal_pricing_sku", "tenant_id", "enterprise_sku_id"),
    )
    pricing_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    category_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    enterprise_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    price_type: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    agreement_price: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    discount_rate: Mapped[float | None] = mapped_column(NUMERIC(6, 4), nullable=True)
    promotion_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    governance_state: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ────────────────────────────── 销售报价与订单 ──────────────────────────────


class SalSalesQuotationORM(Base):
    __tablename__ = "sal_sales_quotation"
    __table_args__ = (
        UniqueConstraint("tenant_id", "quotation_code", name="uq_sal_quotation_code"),
        Index("idx_sal_quotation_customer", "tenant_id", "customer_id"),
        Index("idx_sal_quotation_tenant_status", "tenant_id", "status"),
    )
    quotation_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quotation_code: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_customer.customer_id"), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="CNY")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    governance_state: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    converted_order_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    submitted_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalSalesQuotationLineORM(Base):
    __tablename__ = "sal_sales_quotation_line"
    __table_args__ = (
        UniqueConstraint("quotation_id", "line_number", name="uq_sal_qline_number"),
        Index("idx_sal_qline_quotation", "tenant_id", "quotation_id"),
    )
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quotation_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_sales_quotation.quotation_id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enterprise_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    unit_price: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    expected_delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalSalesOrderORM(Base):
    __tablename__ = "sal_sales_order"
    __table_args__ = (
        UniqueConstraint("tenant_id", "order_code", name="uq_sal_order_code"),
        Index("idx_sal_order_idempotency", "tenant_id", "idempotency_key"),
        Index("idx_sal_order_correlation", "tenant_id", "correlation_id"),
        Index("idx_sal_order_tenant_status", "tenant_id", "status"),
        Index("idx_sal_order_customer_status", "tenant_id", "customer_id", "status"),
    )
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    order_code: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_customer.customer_id"), nullable=False)
    source_quotation_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    shipping_warehouse_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="CNY")
    total_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    reservation_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    credit_check_result: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    submitted_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    correlation_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalSalesOrderLineORM(Base):
    __tablename__ = "sal_sales_order_line"
    __table_args__ = (
        UniqueConstraint("order_id", "line_number", name="uq_sal_oline_number"),
        Index("idx_sal_oline_order", "tenant_id", "order_id"),
    )
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_sales_order.order_id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enterprise_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    ordered_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    reserved_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    shipped_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    unit_price: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    expected_delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pricing_match_result: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    reservation_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ────────────────────────────── 发货与包装与退货 ──────────────────────────────


class SalShipmentOrderORM(Base):
    __tablename__ = "sal_shipment_order"
    __table_args__ = (
        UniqueConstraint("tenant_id", "shipment_code", name="uq_sal_shipment_code"),
        Index("idx_sal_shipment_idempotency", "tenant_id", "idempotency_key"),
        Index("idx_sal_shipment_correlation", "tenant_id", "correlation_id"),
        Index("idx_sal_shipment_tenant_status", "tenant_id", "status"),
    )
    shipment_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    shipment_code: Mapped[str] = mapped_column(String(64), nullable=False)
    order_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    shipping_warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    picking_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="fifo")
    logistics_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    carrier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    wms_picking_task_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    wms_shipping_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    correlation_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalShipmentLineORM(Base):
    __tablename__ = "sal_shipment_line"
    __table_args__ = (Index("idx_sal_sline_shipment", "tenant_id", "shipment_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    shipment_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_shipment_order.shipment_id"), nullable=False)
    order_line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    enterprise_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    ship_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    wms_picking_detail_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalPackingRecordORM(Base):
    __tablename__ = "sal_packing_record"
    __table_args__ = (Index("idx_sal_packing_shipment", "tenant_id", "shipment_id"),)
    packing_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    shipment_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_shipment_order.shipment_id"), nullable=False)
    package_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_gross_weight: Mapped[float] = mapped_column(NUMERIC(18, 4), nullable=False, default=0)
    total_net_weight: Mapped[float] = mapped_column(NUMERIC(18, 4), nullable=False, default=0)
    total_volume: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    packed_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    packed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalPackingLineORM(Base):
    __tablename__ = "sal_packing_line"
    __table_args__ = (Index("idx_sal_pline_packing", "tenant_id", "packing_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    packing_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_packing_record.packing_id"), nullable=False)
    shipment_line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    carton_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    packed_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    gross_weight: Mapped[float] = mapped_column(NUMERIC(18, 4), nullable=False, default=0)
    net_weight: Mapped[float] = mapped_column(NUMERIC(18, 4), nullable=False, default=0)
    volume: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalSalesReturnORM(Base):
    __tablename__ = "sal_sales_return"
    __table_args__ = (
        UniqueConstraint("tenant_id", "return_code", name="uq_sal_return_code"),
        Index("idx_sal_return_idempotency", "tenant_id", "idempotency_key"),
        Index("idx_sal_return_correlation", "tenant_id", "correlation_id"),
        Index("idx_sal_return_order", "tenant_id", "order_id"),
        Index("idx_sal_return_tenant_status", "tenant_id", "status"),
    )
    return_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    return_code: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_sales_order.order_id"), nullable=False)
    original_shipment_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    return_reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    refund_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    wms_receiving_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    correlation_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    submitted_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalReturnLineORM(Base):
    __tablename__ = "sal_return_line"
    __table_args__ = (Index("idx_sal_rline_return", "tenant_id", "return_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    return_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_sales_return.return_id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    order_line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    shipment_line_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    enterprise_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    return_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    refund_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    qc_result: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    disposition: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ────────────────────────────── 结算与发票与收款 ──────────────────────────────


class SalSalesSettlementORM(Base):
    __tablename__ = "sal_sales_settlement"
    __table_args__ = (
        UniqueConstraint("tenant_id", "settlement_code", name="uq_sal_settlement_code"),
        Index("idx_sal_settlement_order", "tenant_id", "order_id"),
        Index("idx_sal_settlement_tenant_status", "tenant_id", "status"),
    )
    settlement_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    settlement_code: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_sales_order.order_id"), nullable=False)
    receivable_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    refund_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    net_receivable_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    invoice_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    payment_receipt_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    revenue_landed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    correlation_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    reconciled_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalSettlementReconcileLineORM(Base):
    __tablename__ = "sal_settlement_reconcile_line"
    __table_args__ = (Index("idx_sal_recline_settlement", "tenant_id", "settlement_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    settlement_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_sales_settlement.settlement_id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    order_line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    enterprise_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    ship_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    diff: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalSalesInvoiceORM(Base):
    __tablename__ = "sal_sales_invoice"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_code", name="uq_sal_invoice_code"),
        Index("idx_sal_invoice_customer", "tenant_id", "customer_id"),
        Index("idx_sal_invoice_tenant_status", "tenant_id", "status"),
    )
    invoice_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    invoice_code: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_customer.customer_id"), nullable=False)
    invoice_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    invoice_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    matched_settlement_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalInvoiceLineORM(Base):
    __tablename__ = "sal_invoice_line"
    __table_args__ = (Index("idx_sal_iline_invoice", "tenant_id", "invoice_id"),)
    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_sales_invoice.invoice_id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enterprise_sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    unit_price: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    tax_rate: Mapped[float] = mapped_column(NUMERIC(6, 4), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalPaymentReceiptORM(Base):
    __tablename__ = "sal_payment_receipt"
    __table_args__ = (
        Index("idx_sal_payment_settlement", "tenant_id", "settlement_id"),
        Index("idx_sal_payment_tenant_status", "tenant_id", "status"),
    )
    payment_receipt_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    settlement_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("sal_sales_settlement.settlement_id"), nullable=False)
    payment_amount: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False, default="bank_transfer")
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    bank_account: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="requested")
    payment_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requested_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ────────────────────────────── 审计 ──────────────────────────────


class SalSalesAuditORM(Base):
    __tablename__ = "sal_sales_audit"
    __table_args__ = (
        Index("idx_sal_audit_tenant_time", "tenant_id", "operated_at"),
        Index("idx_sal_audit_tenant_order", "tenant_id", "order_id"),
        Index("idx_sal_audit_tenant_customer", "tenant_id", "customer_id"),
        Index("idx_sal_audit_tenant_event", "tenant_id", "event_type"),
    )
    audit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    order_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    shipment_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    return_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    settlement_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    invoice_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    payment_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    before_state: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    after_state: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    wms_picking_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    wms_shipping_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    wms_receiving_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    reservation_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    operated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())