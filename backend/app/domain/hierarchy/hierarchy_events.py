"""层级领域事件 - 节点创建、停用、移动。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class HierarchyNodeCreatedEvent(DomainEvent):
    """层级节点创建事件。"""

    tenant_id: UUID
    node_id: UUID
    level: int
    parent_id: UUID | None


@dataclass(frozen=True, kw_only=True)
class HierarchyNodeDisabledEvent(DomainEvent):
    """层级节点停用事件 - 触发级联停用下级节点。"""

    tenant_id: UUID
    node_id: UUID
    level: int


@dataclass(frozen=True, kw_only=True)
class HierarchyNodeMovedEvent(DomainEvent):
    """层级节点移动事件 - 父级变更。"""

    tenant_id: UUID
    node_id: UUID
    old_parent_id: UUID | None
    new_parent_id: UUID | None