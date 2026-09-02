"""PLT OutboxEventAggregate 单元测试 - 至少一次投递 Outbox 事件。

覆盖 create() 初始 PENDING、mark_delivered() 状态与 attempts 自增、
mark_dead_letter() 状态、should_retry() PENDING 且未超 max_attempts、
达到 max_attempts 不再重试、frozen dataclass 不可变性。
"""

from __future__ import annotations

import os
import sys
from dataclasses import FrozenInstanceError, is_dataclass
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.domain.platform.consistency.aggregates.outbox_event_aggregate import (
    DeliveryStatus,
    OutboxEventAggregate,
)


def _make_event(max_attempts: int = 10) -> OutboxEventAggregate:
    return OutboxEventAggregate.create(
        tenant_id=uuid4(),
        aggregate_root_type="TenantLifecycle",
        aggregate_root_id="tenant-001",
        event_type="tenant.frozen",
        payload={"reason": "overdue"},
        trace_id="trace-001",
        max_attempts=max_attempts,
    )


class OutboxEventAggregateTest:
    """OutboxEventAggregate 投递状态机测试。"""

    def test_create_sets_delivery_status_to_pending(self) -> None:
        event = _make_event()
        assert event.delivery_status == DeliveryStatus.PENDING
        assert event.delivery_attempts == 0
        assert event.last_delivered_at is None
        assert event.event_version == 1

    def test_mark_delivered_changes_status_and_increments_attempts(self) -> None:
        event = _make_event()
        delivered = event.mark_delivered()
        assert delivered.delivery_status == DeliveryStatus.DELIVERED
        assert delivered.delivery_attempts == event.delivery_attempts + 1
        assert delivered.last_delivered_at is not None
        # 原实例不可变
        assert event.delivery_status == DeliveryStatus.PENDING

    def test_mark_dead_letter_changes_status(self) -> None:
        event = _make_event()
        dead = event.mark_dead_letter()
        assert dead.delivery_status == DeliveryStatus.DEAD_LETTER
        assert dead.delivery_attempts == event.delivery_attempts + 1
        assert dead.last_delivered_at is not None

    def test_should_retry_true_when_pending_and_attempts_below_max(self) -> None:
        event = _make_event(max_attempts=10)
        assert event.delivery_status == DeliveryStatus.PENDING
        assert event.delivery_attempts < event.max_attempts
        assert event.should_retry() is True

    def test_should_retry_false_when_attempts_reach_max(self) -> None:
        # 构造一个 attempts 已达 max_attempts 的 PENDING 事件
        event = OutboxEventAggregate(
            event_id=uuid4(),
            tenant_id=uuid4(),
            aggregate_root_type="X",
            aggregate_root_id="1",
            event_type="x",
            event_version=1,
            payload={},
            trace_id="t",
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            delivery_status=DeliveryStatus.PENDING,
            delivery_attempts=10,
            last_delivered_at=None,
            max_attempts=10,
        )
        assert event.should_retry() is False

    def test_should_retry_false_when_already_delivered(self) -> None:
        event = _make_event()
        delivered = event.mark_delivered()
        # DELIVERED 状态不再重试
        assert delivered.should_retry() is False

    def test_frozen_dataclass_is_immutable(self) -> None:
        event = _make_event()
        assert is_dataclass(event)
        with pytest.raises(FrozenInstanceError):
            event.delivery_status = DeliveryStatus.DELIVERED  # type: ignore[misc]