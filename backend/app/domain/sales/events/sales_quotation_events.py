"""SAL 销售报价领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SalesQuotationApprovedEvent:
    """销售报价审批通过事件。"""

    quotation_id: UUID
    tenant_id: UUID
    customer_id: UUID
    approved_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SalesQuotationConvertedEvent:
    """报价转销售订单事件。"""

    quotation_id: UUID
    tenant_id: UUID
    order_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))