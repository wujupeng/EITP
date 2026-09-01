"""SAL 信用额度领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CreditLimitOccupiedEvent:
    """信用额度占用事件。"""

    customer_id: UUID
    tenant_id: UUID
    order_id: UUID
    occupied_amount: float
    used_amount: float
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CreditLimitReleasedEvent:
    """信用额度释放事件。"""

    customer_id: UUID
    tenant_id: UUID
    released_amount: float
    used_amount: float
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))