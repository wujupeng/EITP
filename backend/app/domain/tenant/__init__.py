"""Tenant Bounded Context - 租户生命周期管理。"""

from app.domain.tenant.tenant_aggregate import TenantAggregate
from app.domain.tenant.tenant_events import (
    TenantDeprovisionedEvent,
    TenantDisabledEvent,
    TenantProvisionFailedEvent,
    TenantProvisionedEvent,
)
from app.domain.tenant.tenant_state import DataPlacement, TenantStatus

__all__ = [
    "DataPlacement",
    "TenantAggregate",
    "TenantDeprovisionedEvent",
    "TenantDisabledEvent",
    "TenantProvisionFailedEvent",
    "TenantProvisionedEvent",
    "TenantStatus",
]
