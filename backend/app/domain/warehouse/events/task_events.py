"""WMS Task 领域事件。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class WmsTaskCreatedEvent(DomainEvent):
    """Task 创建事件。"""
    tenant_id: UUID
    task_id: UUID
    task_type: str
    document_id: UUID
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class WmsTaskAssignedEvent(DomainEvent):
    """Task 分配事件。"""
    tenant_id: UUID
    task_id: UUID
    assignee_id: UUID
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class WmsTaskClaimedEvent(DomainEvent):
    """Task 领取事件。"""
    tenant_id: UUID
    task_id: UUID
    user_id: UUID
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class WmsTaskCompletedEvent(DomainEvent):
    """Task 完成事件。"""
    tenant_id: UUID
    task_id: UUID
    inv_transaction_ids: list[UUID]
    duration_ms: float | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class WmsTaskCancelledEvent(DomainEvent):
    """Task 取消事件。"""
    tenant_id: UUID
    task_id: UUID
    reason: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class WmsTaskFailedEvent(DomainEvent):
    """Task 失败事件。"""
    tenant_id: UUID
    task_id: UUID
    failure_reason: str
    correlation_id: str | None = None