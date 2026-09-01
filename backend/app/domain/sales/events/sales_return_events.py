"""SAL 销售退货领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SalesReturnCompletedEvent:
    """销售退货完成事件 - 供销售结算（退款冲抵）/BI-001 订阅。"""

    return_id: UUID
    tenant_id: UUID
    order_id: UUID
    refund_amount: float
    disposition: str
    wms_receiving_id: UUID | None = None
    inv_transaction_ids: list[str] = field(default_factory=list)
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))