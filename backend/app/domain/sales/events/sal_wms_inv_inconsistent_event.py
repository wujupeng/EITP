"""SAL 销售↔WMS↔INV 三边不一致领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SalWmsInvInconsistentEvent:
    """销售↔WMS↔INV 三边不一致事件 - 供运维告警。"""

    tenant_id: UUID
    order_id: UUID
    shipment_id: UUID | None
    sku_id: UUID
    sal_qty: float
    wms_qty: float
    inv_qty: float
    diff: float
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))