"""收货/上架领域事件。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ReceivingCompletedEvent(DomainEvent):
    """收货完成事件 - 供 PUR-001/BI-001 订阅。"""
    tenant_id: UUID
    receiving_id: UUID
    sku_id: UUID
    quantity: float
    warehouse_id: UUID
    location_id: UUID
    inv_transaction_ids: list[UUID]
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class PutawayCompletedEvent(DomainEvent):
    """上架完成事件 - 供 PUR-001/BI-001 订阅。"""
    tenant_id: UUID
    putaway_task_id: UUID
    sku_id: UUID
    quantity: float
    target_location_id: UUID
    inv_transaction_ids: list[UUID]
    correlation_id: str | None = None