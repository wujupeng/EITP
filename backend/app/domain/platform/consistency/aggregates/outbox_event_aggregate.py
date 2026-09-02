"""Outbox 事件聚合根 - 保证至少一次投递。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    CONFIRMED = "CONFIRMED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass(frozen=True)
class OutboxEventAggregate:
    """Outbox 事件聚合根 - 业务事务内写入，异步投递器保证至少一次投递。"""

    event_id: UUID
    tenant_id: UUID
    aggregate_root_type: str
    aggregate_root_id: str
    event_type: str
    event_version: int
    payload: dict
    trace_id: str
    created_at: datetime
    delivery_status: DeliveryStatus
    delivery_attempts: int
    last_delivered_at: datetime | None
    max_attempts: int

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        aggregate_root_type: str,
        aggregate_root_id: str,
        event_type: str,
        payload: dict,
        trace_id: str,
        event_version: int = 1,
        max_attempts: int = 10,
    ) -> OutboxEventAggregate:
        return cls(
            event_id=uuid4(),
            tenant_id=tenant_id,
            aggregate_root_type=aggregate_root_type,
            aggregate_root_id=aggregate_root_id,
            event_type=event_type,
            event_version=event_version,
            payload=payload,
            trace_id=trace_id,
            created_at=datetime.now(timezone.utc),
            delivery_status=DeliveryStatus.PENDING,
            delivery_attempts=0,
            last_delivered_at=None,
            max_attempts=max_attempts,
        )

    def mark_delivered(self) -> OutboxEventAggregate:
        return OutboxEventAggregate(
            event_id=self.event_id,
            tenant_id=self.tenant_id,
            aggregate_root_type=self.aggregate_root_type,
            aggregate_root_id=self.aggregate_root_id,
            event_type=self.event_type,
            event_version=self.event_version,
            payload=self.payload,
            trace_id=self.trace_id,
            created_at=self.created_at,
            delivery_status=DeliveryStatus.DELIVERED,
            delivery_attempts=self.delivery_attempts + 1,
            last_delivered_at=datetime.now(timezone.utc),
            max_attempts=self.max_attempts,
        )

    def mark_dead_letter(self) -> OutboxEventAggregate:
        return OutboxEventAggregate(
            event_id=self.event_id,
            tenant_id=self.tenant_id,
            aggregate_root_type=self.aggregate_root_type,
            aggregate_root_id=self.aggregate_root_id,
            event_type=self.event_type,
            event_version=self.event_version,
            payload=self.payload,
            trace_id=self.trace_id,
            created_at=self.created_at,
            delivery_status=DeliveryStatus.DEAD_LETTER,
            delivery_attempts=self.delivery_attempts + 1,
            last_delivered_at=datetime.now(timezone.utc),
            max_attempts=self.max_attempts,
        )

    def should_retry(self) -> bool:
        return (
            self.delivery_status == DeliveryStatus.PENDING
            and self.delivery_attempts < self.max_attempts
        )