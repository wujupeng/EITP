"""SAL 客户领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CustomerPublishedEvent:
    """客户审批发布生效事件。"""

    customer_id: UUID
    tenant_id: UUID
    customer_code: str
    status: str = "active"
    published_version: int = 1
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CustomerDisabledEvent:
    """客户停用事件。"""

    customer_id: UUID
    tenant_id: UUID
    customer_code: str
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))