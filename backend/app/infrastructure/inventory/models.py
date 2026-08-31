"""INV ORM 模型 - 所有 inv_* 表。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Float,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProductORM(Base):
    __tablename__ = "inv_product"
    __table_args__ = (
        UniqueConstraint("tenant_id", "product_code", name="uq_inv_product_tenant_code"),
        Index("ix_inv_product_tenant", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    brand_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    base_unit_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SkuORM(Base):
    __tablename__ = "inv_sku"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku_code", name="uq_inv_sku_tenant_code"),
        Index("ix_inv_sku_tenant", "tenant_id"),
        Index("ix_inv_sku_product", "product_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    product_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_code: Mapped[str] = mapped_column(String(50), nullable=False)
    sku_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specification: Mapped[str | None] = mapped_column(Text, nullable=True)
    barcode_list: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CategoryORM(Base):
    __tablename__ = "inv_category"
    __table_args__ = (
        UniqueConstraint("tenant_id", "category_code", name="uq_inv_category_tenant_code"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    category_name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_category_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrandORM(Base):
    __tablename__ = "inv_brand"
    __table_args__ = (
        UniqueConstraint("tenant_id", "brand_code", name="uq_inv_brand_tenant_code"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    brand_code: Mapped[str] = mapped_column(String(50), nullable=False)
    brand_name: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UnitORM(Base):
    __tablename__ = "inv_unit"
    __table_args__ = (
        UniqueConstraint("tenant_id", "unit_code", name="uq_inv_unit_tenant_code"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(50), nullable=False)
    unit_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_base_unit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LocationConfigORM(Base):
    __tablename__ = "inv_location_config"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    location_type: Mapped[str] = mapped_column(String(20), nullable=False, default="storage")
    capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_enforce_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="warn")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryLedgerORM(Base):
    """库存账本 - append-only 事实源。"""
    __tablename__ = "inv_inventory_ledger"
    __table_args__ = (
        Index("ix_inv_ledger_tenant_sku_wh", "tenant_id", "sku_id", "warehouse_id"),
        Index("ix_inv_ledger_transaction", "transaction_id"),
        CheckConstraint(
            "quantity_after = quantity_before + quantity_change",
            name="ck_inv_ledger_qty_consistency",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    site_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity_before: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_change: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_after: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operated_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    operated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryBalanceORM(Base):
    """库存余额 - 六状态量快照。"""
    __tablename__ = "inv_inventory_balance"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "sku_id", "warehouse_id", "location_id", "batch_no",
            name="uq_inv_balance_key",
        ),
        Index("ix_inv_balance_tenant_sku_wh", "tenant_id", "sku_id", "warehouse_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    batch_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    on_hand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reserved: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    in_transit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    inspection: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    blocked: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_ledger_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryReservationORM(Base):
    __tablename__ = "inv_inventory_reservation"
    __table_args__ = (
        Index("ix_inv_reservation_tenant_sku", "tenant_id", "sku_id"),
        Index("ix_inv_reservation_status_expires", "status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    site_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    reserved_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    document_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryTransactionORM(Base):
    __tablename__ = "inv_inventory_transaction"
    __table_args__ = (
        Index("ix_inv_tx_tenant_idem", "tenant_id", "idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    site_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    result_ledger_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdempotencyRecordORM(Base):
    __tablename__ = "inv_idempotency_record"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_inv_idem_tenant_key"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    transaction_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentORM(Base):
    __tablename__ = "inv_document"
    __table_args__ = (
        UniqueConstraint("tenant_id", "document_number", name="uq_inv_doc_tenant_number"),
        Index("ix_inv_doc_tenant_type", "tenant_id", "document_type"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    document_number: Mapped[str] = mapped_column(String(50), nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    site_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    warehouse_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    executed_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentLineORM(Base):
    __tablename__ = "inv_document_line"
    __table_args__ = (
        Index("ix_inv_doc_line_document", "document_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    warehouse_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NegativeStockPolicyORM(Base):
    __tablename__ = "inv_negative_stock_policy"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_inv_neg_policy_tenant"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), nullable=False, default="global_forbid")
    allow_force: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    require_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryAuditORM(Base):
    """库存审计 - 不可篡改，仅追加。"""
    __tablename__ = "inv_inventory_audit"
    __table_args__ = (
        Index("ix_inv_audit_tenant_sku", "tenant_id", "sku_id"),
        Index("ix_inv_audit_document", "document_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sku_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    warehouse_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    document_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    quantity_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    transaction_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())