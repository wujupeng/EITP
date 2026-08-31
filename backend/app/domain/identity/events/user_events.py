"""用户领域事件。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserActivatedEvent(DomainEvent):
    user_id: UUID
    tenant_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserLockedEvent(DomainEvent):
    user_id: UUID
    tenant_id: UUID
    duration_minutes: int


@dataclass(frozen=True, kw_only=True)
class UserDisabledEvent(DomainEvent):
    user_id: UUID
    tenant_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserDeactivatedEvent(DomainEvent):
    user_id: UUID
    tenant_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserPasswordChangedEvent(DomainEvent):
    user_id: UUID
    tenant_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserLoginSucceededEvent(DomainEvent):
    user_id: UUID
    tenant_id: UUID
    ip_address: str


@dataclass(frozen=True, kw_only=True)
class UserLoginFailedEvent(DomainEvent):
    user_id: UUID | None
    tenant_id: UUID | None
    username: str
    ip_address: str
    reason: str