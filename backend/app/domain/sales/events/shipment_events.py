"""SAL 发货领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ShipmentConfirmedEvent:
    """发货确认事件 - 供销售结算（驱动对账）/BI-001 订阅。"""

    shipment_id: UUID
    tenant_id: UUID
    order_ids: list[str]
    wms_shipping_id: UUID
    inv_transaction_ids: list[str]
    logistics_no: str
    total_ship_quantity: float
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ShipmentFailedEvent:
    """发货失败事件 - WMS 失败，库存不变可重试。"""

    shipment_id: UUID
    tenant_id: UUID
    failure_reason: str
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))