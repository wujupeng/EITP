"""租户领域事件。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class TenantProvisionedEvent(DomainEvent):
    """租户开通完成事件。"""

    tenant_id: UUID
    enterprise_name: str


@dataclass(frozen=True, kw_only=True)
class TenantDisabledEvent(DomainEvent):
    """租户停用事件。"""

    tenant_id: UUID


@dataclass(frozen=True, kw_only=True)
class TenantDeprovisionedEvent(DomainEvent):
    """租户注销事件。"""

    tenant_id: UUID


@dataclass(frozen=True, kw_only=True)
class TenantProvisionFailedEvent(DomainEvent):
    """租户开通失败事件。"""

    tenant_id: UUID
    reason: str