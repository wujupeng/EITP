"""库存位置变更领域事件。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PositionChangedEvent(DomainEvent):
    """库存位置变更事件 - 数量增减/状态变更/库位转移。"""

    tenant_id: UUID
    position_id: UUID
    sku_id: UUID
    location_id: UUID
    change_type: str
    before_state: dict | None = None
    after_state: dict | None = None


@dataclass(frozen=True, kw_only=True)
class WmsInvInconsistentEvent(DomainEvent):
    """WMS 与 INV 库存不一致事件 - 对账发现差异时发布。"""

    tenant_id: UUID
    warehouse_id: UUID
    sku_id: UUID
    wms_qty: float
    inv_qty: float
    diff: float
    location_id: UUID | None = None