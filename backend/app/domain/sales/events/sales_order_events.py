"""SAL 销售订单领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SalesOrderCreatedEvent:
    """销售订单创建事件。"""

    order_id: UUID
    tenant_id: UUID
    customer_id: UUID
    total_amount: float
    correlation_id: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SalesOrderApprovedEvent:
    """销售订单审批通过事件。"""

    order_id: UUID
    tenant_id: UUID
    approved_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SalesOrderReservedEvent:
    """销售订单确认履约预留成功事件。"""

    order_id: UUID
    tenant_id: UUID
    reservation_ids: list[str]
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SalesOrderChangedEvent:
    """销售订单变更事件。"""

    order_id: UUID
    tenant_id: UUID
    version: int
    before: dict[str, Any]
    after: dict[str, Any]
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SalesOrderCancelledEvent:
    """销售订单取消事件。"""

    order_id: UUID
    tenant_id: UUID
    cancelled_quantity: float
    reason: str = ""
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))