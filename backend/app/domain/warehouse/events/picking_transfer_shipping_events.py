"""拣货/移库/发货领域事件。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PickingCompletedEvent(DomainEvent):
    """拣货完成事件。"""
    tenant_id: UUID
    picking_task_id: UUID
    source_order_id: UUID
    inv_transaction_ids: list[UUID]
    reservation_id: UUID | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class TransferCompletedEvent(DomainEvent):
    """移库完成事件。"""
    tenant_id: UUID
    transfer_order_id: UUID
    warehouse_id: UUID
    inv_transaction_ids: list[UUID]
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class ShippingCompletedEvent(DomainEvent):
    """发货完成事件。"""
    tenant_id: UUID
    shipping_order_id: UUID
    source_order_id: UUID
    logistics_no: str
    logistics_company: str
    inv_transaction_ids: list[UUID]
    correlation_id: str | None = None