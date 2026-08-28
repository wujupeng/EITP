"""聚合根基类 - 一致性边界的入口，管理领域事件收集。"""

from __future__ import annotations

from collections.abc import Collection

from app.domain.shared.domain_event import DomainEvent
from app.domain.shared.entity import Entity


class AggregateRoot(Entity):
    """聚合根基类 - 维护聚合内一致性边界，收集待发布领域事件。"""

    def __init__(self, id: object) -> None:
        super().__init__(id)
        self._events: list[DomainEvent] = []

    def _record_event(self, event: DomainEvent) -> None:
        """记录领域事件，待持久化后由 DomainEventBus 发布。"""
        self._events.append(event)

    def pull_events(self) -> Collection[DomainEvent]:
        """提取并清空待发布事件 - 持久化成功后调用。"""
        events = list(self._events)
        self._events.clear()
        return events

    def clear_events(self) -> None:
        self._events.clear()