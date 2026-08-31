"""WMS ORM 模型 - 所有 wms_* 表。

企业级表含 tenant_id（租户隔离），复用 MDM Base。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Date,
    Text,
    Index,
    UniqueConstraint,
    func,
    CheckConstraint,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infrastructure.mdm.models import Base


class WmsWarehouseORM(Base):
    __tablename__ = "wms_warehouse"
    __table_args__ = (
        UniqueConstraint("tenant_id", "warehouse_code", name="uk_wms_warehouse_code"),
        CheckConstraint("status IN ('active', 'disabled')", name="chk_wms_warehouse_status"),
        Index("idx_wms_warehouse_tenant_status", "tenant_id", "status"),
    )

    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    hierarchy_node_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    warehouse_code: Mapped[str] = mapped_column(String(64), nullable=False)
    warehouse_name: Mapped[str] = mapped_column(String(256), nullable=False)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    wms_config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsZoneORM(Base):
    __tablename__ = "wms_zone"
    __table_args__ = (
        UniqueConstraint("tenant_id", "warehouse_id", "zone_code", name="uk_wms_zone_code"),
        CheckConstraint("zone_function IN ('receiving','storage','picking','shipping','qc','blocked')", name="chk_wms_zone_function"),
        CheckConstraint("status IN ('active','disabled')", name="chk_wms_zone_status"),
        Index("idx_wms_zone_warehouse", "tenant_id", "warehouse_id"),
        Index("idx_wms_zone_function", "tenant_id", "zone_function", "status"),
    )

    zone_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_warehouse.warehouse_id"), nullable=False)
    zone_code: Mapped[str] = mapped_column(String(64), nullable=False)
    zone_name: Mapped[str] = mapped_column(String(256), nullable=False)
    zone_function: Mapped[str] = mapped_column(String(16), nullable=False, default="storage")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsAreaORM(Base):
    __tablename__ = "wms_area"
    __table_args__ = (
        UniqueConstraint("tenant_id", "zone_id", "area_code", name="uk_wms_area_code"),
        CheckConstraint("status IN ('active','disabled')", name="chk_wms_area_status"),
        Index("idx_wms_area_zone", "tenant_id", "zone_id"),
    )

    area_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    zone_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_zone.zone_id"), nullable=False)
    area_code: Mapped[str] = mapped_column(String(64), nullable=False)
    area_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsLocationORM(Base):
    __tablename__ = "wms_location"
    __table_args__ = (
        UniqueConstraint("tenant_id", "warehouse_id", "location_code", name="uk_wms_location_code"),
        CheckConstraint("location_type IN ('floor','shelf','cold','frozen')", name="chk_wms_location_type"),
        CheckConstraint("capacity_enforce_mode IN ('warn','reject')", name="chk_wms_location_enforce"),
        CheckConstraint("status IN ('active','disabled')", name="chk_wms_location_status"),
        Index("idx_wms_location_zone", "tenant_id", "zone_id"),
        Index("idx_wms_location_wh_status", "tenant_id", "warehouse_id", "status"),
        Index("idx_wms_location_area", "tenant_id", "area_id"),
    )

    location_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_warehouse.warehouse_id"), nullable=False)
    zone_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_zone.zone_id"), nullable=False)
    area_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_area.area_id"), nullable=True)
    location_code: Mapped[str] = mapped_column(String(64), nullable=False)
    location_type: Mapped[str] = mapped_column(String(16), nullable=False, default="shelf")
    capacity_max_qty: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    capacity_max_weight: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    capacity_max_volume: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    capacity_enforce_mode: Mapped[str] = mapped_column(String(8), nullable=False, default="reject")
    coordinate_x: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    coordinate_y: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    coordinate_z: Mapped[float | None] = mapped_column(NUMERIC(18, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsBinORM(Base):
    __tablename__ = "wms_bin"
    __table_args__ = (
        UniqueConstraint("tenant_id", "location_id", "bin_code", name="uk_wms_bin_code"),
        CheckConstraint("status IN ('active','inactive')", name="chk_wms_bin_status"),
        Index("idx_wms_bin_location", "tenant_id", "location_id"),
    )

    bin_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    location_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=False)
    bin_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsEquipmentORM(Base):
    __tablename__ = "wms_equipment"
    __table_args__ = (
        UniqueConstraint("tenant_id", "warehouse_id", "equipment_code", name="uk_wms_equipment_code"),
        CheckConstraint("equipment_type IN ('forklift','pda','scanner','conveyor','agv')", name="chk_wms_equipment_type"),
        CheckConstraint("status IN ('active','inactive','maintenance')", name="chk_wms_equipment_status"),
        Index("idx_wms_equipment_warehouse", "tenant_id", "warehouse_id", "status"),
    )

    equipment_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_warehouse.warehouse_id"), nullable=False)
    equipment_code: Mapped[str] = mapped_column(String(64), nullable=False)
    equipment_type: Mapped[str] = mapped_column(String(16), nullable=False, default="forklift")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsTaskORM(Base):
    __tablename__ = "wms_task"
    __table_args__ = (
        CheckConstraint("task_type IN ('receiving','putaway','picking','transfer','shipping','packing','cycle_count','qc')", name="chk_wms_task_type"),
        CheckConstraint("status IN ('created','assigned','in_progress','completed','cancelled','failed')", name="chk_wms_task_status"),
        CheckConstraint("priority IN ('high','medium','low')", name="chk_wms_task_priority"),
        Index("idx_wms_task_status", "tenant_id", "status"),
        Index("idx_wms_task_assignee", "tenant_id", "assignee_id", "status"),
        Index("idx_wms_task_document", "tenant_id", "document_id"),
    )

    task_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    task_type: Mapped[str] = mapped_column(String(16), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    assignee_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="created")
    priority: Mapped[str] = mapped_column(String(8), nullable=False, default="medium")
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WmsTaskLineORM(Base):
    __tablename__ = "wms_task_line"
    __table_args__ = (
        UniqueConstraint("task_id", "line_no", name="uk_wms_task_line_no"),
        CheckConstraint("status IN ('pending','in_progress','completed','cancelled','failed')", name="chk_wms_task_line_status"),
        Index("idx_wms_task_line_task", "tenant_id", "task_id"),
        Index("idx_wms_task_line_sku", "tenant_id", "sku_id"),
    )

    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_task.task_id"), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=True)
    target_location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=True)
    required_qty: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    executed_qty: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsInventoryPositionORM(Base):
    __tablename__ = "wms_inventory_position"
    __table_args__ = (
        CheckConstraint("inventory_status IN ('available','in_qc','blocked','in_transit','quarantined','returned')", name="chk_wms_position_status"),
        Index("idx_wms_position_sku_wh", "tenant_id", "sku_id", "warehouse_id"),
        Index("idx_wms_position_location", "tenant_id", "location_id"),
        Index("idx_wms_position_sku_status", "tenant_id", "sku_id", "inventory_status"),
        Index("idx_wms_position_reconcile", "tenant_id", "sku_id", "warehouse_id", "inventory_status"),
    )

    position_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_warehouse.warehouse_id"), nullable=False)
    location_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=False)
    bin_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_bin.bin_id"), nullable=True)
    lot_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    inventory_status: Mapped[str] = mapped_column(String(16), nullable=False, default="available")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsReceivingOrderORM(Base):
    __tablename__ = "wms_receiving_order"
    __table_args__ = (
        CheckConstraint("status IN ('draft','submitted','executing','completed')", name="chk_wms_recv_status"),
        Index("idx_wms_recv_tenant_status", "tenant_id", "status"),
        Index("idx_wms_recv_source_doc", "tenant_id", "source_document_id"),
    )

    receiving_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    source_document_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    source_document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_warehouse.warehouse_id"), nullable=False)
    zone_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_zone.zone_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    over_receive_ratio: Mapped[float] = mapped_column(NUMERIC(6, 4), nullable=False, default=0)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsReceivingLineORM(Base):
    __tablename__ = "wms_receiving_line"
    __table_args__ = (
        Index("idx_wms_recv_line_order", "tenant_id", "receiving_id"),
        Index("idx_wms_recv_line_sku", "tenant_id", "sku_id"),
    )

    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    receiving_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_receiving_order.receiving_id"), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    ordered_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    received_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=True)
    is_inspection_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    batch_lot: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsPutawayTaskORM(Base):
    __tablename__ = "wms_putaway_task"
    __table_args__ = (
        CheckConstraint("status IN ('pending','target_set','executing','completed','cancelled')", name="chk_wms_putaway_status"),
        CheckConstraint("putaway_strategy IN ('manual','nearest','empty_first','same_sku','same_product_concentrate','zoned','by_turnover')", name="chk_wms_putaway_strategy"),
        Index("idx_wms_putaway_tenant_status", "tenant_id", "status"),
        Index("idx_wms_putaway_source_loc", "tenant_id", "source_location_id"),
        Index("idx_wms_putaway_sku", "tenant_id", "sku_id", "status"),
    )

    putaway_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    source_location_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=False)
    target_location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=True)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    putaway_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    putaway_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_document_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsPickingTaskORM(Base):
    __tablename__ = "wms_picking_task"
    __table_args__ = (
        CheckConstraint("status IN ('draft','reserved','executing','completed','cancelled')", name="chk_wms_picking_status"),
        CheckConstraint("picking_strategy IN ('fifo','lifo','fefo','manual','by_location','by_batch')", name="chk_wms_picking_strategy"),
        Index("idx_wms_picking_tenant_status", "tenant_id", "status"),
        Index("idx_wms_picking_source_order", "tenant_id", "source_order_id"),
    )

    picking_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    source_order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    source_order_type: Mapped[str] = mapped_column(String(32), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_warehouse.warehouse_id"), nullable=False)
    picking_strategy: Mapped[str] = mapped_column(String(16), nullable=False, default="fifo")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    reservation_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsPickingLineORM(Base):
    __tablename__ = "wms_picking_line"
    __table_args__ = (
        Index("idx_wms_picking_line_task", "tenant_id", "picking_task_id"),
        Index("idx_wms_picking_line_sku_loc", "tenant_id", "sku_id", "source_location_id"),
    )

    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    picking_task_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_picking_task.picking_id"), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    source_location_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=False)
    required_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    picked_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    strategy: Mapped[str] = mapped_column(String(16), nullable=False, default="fifo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsTransferOrderORM(Base):
    __tablename__ = "wms_transfer_order"
    __table_args__ = (
        CheckConstraint("status IN ('draft','submitted','approved','rejected','executing','completed','cancelled')", name="chk_wms_transfer_status"),
        Index("idx_wms_transfer_tenant_status", "tenant_id", "status"),
        Index("idx_wms_transfer_warehouse", "tenant_id", "warehouse_id", "status"),
    )

    transfer_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_warehouse.warehouse_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    require_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approver_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_opinion: Mapped[str | None] = mapped_column(String(512), nullable=True)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsTransferLineORM(Base):
    __tablename__ = "wms_transfer_line"
    __table_args__ = (
        Index("idx_wms_transfer_line_order", "tenant_id", "transfer_order_id"),
        Index("idx_wms_transfer_line_sku", "tenant_id", "sku_id"),
    )

    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    transfer_order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_transfer_order.transfer_id"), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    source_location_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=False)
    target_location_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=False)
    quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    transferred_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsShippingOrderORM(Base):
    __tablename__ = "wms_shipping_order"
    __table_args__ = (
        CheckConstraint("status IN ('draft','executing','completed','cancelled')", name="chk_wms_shipping_status"),
        Index("idx_wms_shipping_tenant_status", "tenant_id", "status"),
        Index("idx_wms_shipping_source_order", "tenant_id", "source_order_id"),
    )

    shipping_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    source_order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_warehouse.warehouse_id"), nullable=False)
    zone_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_zone.zone_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    picking_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    logistics_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    logistics_company: Mapped[str | None] = mapped_column(String(128), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inv_transaction_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsShippingLineORM(Base):
    __tablename__ = "wms_shipping_line"
    __table_args__ = (
        Index("idx_wms_shipping_line_order", "tenant_id", "shipping_order_id"),
        Index("idx_wms_shipping_line_sku", "tenant_id", "sku_id"),
    )

    line_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    shipping_order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_shipping_order.shipping_id"), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    logistics_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsOperationAuditORM(Base):
    __tablename__ = "wms_operation_audit"
    __table_args__ = (
        Index("idx_wms_audit_operated", "tenant_id", "operated_at"),
        Index("idx_wms_audit_task", "tenant_id", "task_id"),
        Index("idx_wms_audit_sku_loc", "tenant_id", "sku_id", "location_id"),
        Index("idx_wms_audit_event", "tenant_id", "event_type", "operated_at"),
    )

    audit_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    task_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    sku_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    warehouse_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    inv_transaction_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    operated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WmsReconcileDiffORM(Base):
    __tablename__ = "wms_reconcile_diff"
    __table_args__ = (
        CheckConstraint("diff_type IN ('wms_more','inv_more','match_mismatch')", name="chk_wms_reconcile_diff_type"),
        CheckConstraint("status IN ('open','resolved','ignored')", name="chk_wms_reconcile_status"),
        Index("idx_wms_reconcile_status", "tenant_id", "status"),
        Index("idx_wms_reconcile_sku_wh", "tenant_id", "sku_id", "warehouse_id"),
        Index("idx_wms_reconcile_created", "tenant_id", "created_at"),
    )

    diff_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    sku_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_warehouse.warehouse_id"), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("wms_location.location_id"), nullable=True)
    wms_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    inv_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    diff_quantity: Mapped[float] = mapped_column(NUMERIC(18, 6), nullable=False)
    diff_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())