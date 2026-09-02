"""租户生命周期聚合根 - 冻结/注销/归档状态机。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class TenantLifecycleState(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    ARCHIVED = "ARCHIVED"
    DEPROVISIONING = "DEPROVISIONING"
    DEPROVISIONED = "DEPROVISIONED"


_VALID_TRANSITIONS: dict[TenantLifecycleState, set[TenantLifecycleState]] = {
    TenantLifecycleState.ACTIVE: {TenantLifecycleState.FROZEN, TenantLifecycleState.DEPROVISIONING},
    TenantLifecycleState.FROZEN: {TenantLifecycleState.ACTIVE, TenantLifecycleState.DEPROVISIONING},
    TenantLifecycleState.ARCHIVED: set(),
    TenantLifecycleState.DEPROVISIONING: {TenantLifecycleState.ARCHIVED, TenantLifecycleState.ACTIVE},
    TenantLifecycleState.DEPROVISIONED: set(),
}


@dataclass(frozen=True)
class TenantLifecycleAggregate:
    """租户生命周期聚合根 - 扩展 MT-001 状态机。"""

    tenant_id: UUID
    state: TenantLifecycleState
    updated_at: datetime
    reason: str | None

    @classmethod
    def create(cls, tenant_id: UUID) -> TenantLifecycleAggregate:
        return cls(
            tenant_id=tenant_id,
            state=TenantLifecycleState.ACTIVE,
            updated_at=datetime.now(timezone.utc),
            reason=None,
        )

    def freeze(self, reason: str) -> TenantLifecycleAggregate:
        return self._transition(TenantLifecycleState.FROZEN, reason)

    def unfreeze(self, reason: str) -> TenantLifecycleAggregate:
        return self._transition(TenantLifecycleState.ACTIVE, reason)

    def archive(self, reason: str) -> TenantLifecycleAggregate:
        return self._transition(TenantLifecycleState.ARCHIVED, reason)

    def start_deprovision(self, reason: str) -> TenantLifecycleAggregate:
        return self._transition(TenantLifecycleState.DEPROVISIONING, reason)

    def complete_deprovision(self, reason: str) -> TenantLifecycleAggregate:
        return self._transition(TenantLifecycleState.DEPROVISIONED, reason)

    def _transition(self, new_state: TenantLifecycleState, reason: str) -> TenantLifecycleAggregate:
        if new_state not in _VALID_TRANSITIONS.get(self.state, set()):
            from app.domain.platform.error_codes import PLTErrorCode
            from app.domain.platform.exceptions import PLTError
            raise PLTError(
                PLTErrorCode.TENANT_INVALID_TRANSITION,
                f"非法状态转换: {self.state.value} -> {new_state.value}",
            )
        return TenantLifecycleAggregate(
            tenant_id=self.tenant_id,
            state=new_state,
            updated_at=datetime.now(timezone.utc),
            reason=reason,
        )

    def is_active(self) -> bool:
        return self.state == TenantLifecycleState.ACTIVE

    def is_frozen(self) -> bool:
        return self.state == TenantLifecycleState.FROZEN

    def is_archived(self) -> bool:
        return self.state == TenantLifecycleState.ARCHIVED


@dataclass(frozen=True)
class TenantQuotaAggregate:
    """租户配额聚合根 - 资源使用限制。"""

    tenant_id: UUID
    max_users: int
    max_orders_per_day: int
    max_storage_mb: int
    max_api_calls_per_minute: int
    max_concurrent_requests: int
    current_usage: dict
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        max_users: int = 100,
        max_orders_per_day: int = 10000,
        max_storage_mb: int = 10240,
        max_api_calls_per_minute: int = 1000,
        max_concurrent_requests: int = 100,
    ) -> TenantQuotaAggregate:
        return cls(
            tenant_id=tenant_id,
            max_users=max_users,
            max_orders_per_day=max_orders_per_day,
            max_storage_mb=max_storage_mb,
            max_api_calls_per_minute=max_api_calls_per_minute,
            max_concurrent_requests=max_concurrent_requests,
            current_usage={},
            updated_at=datetime.now(timezone.utc),
        )

    def check_quota(self, resource: str, requested: int) -> bool:
        max_key = f"max_{resource}"
        max_val = getattr(self, max_key, None)
        if max_val is None:
            return True
        current = self.current_usage.get(resource, 0)
        return current + requested <= max_val

    def record_usage(self, resource: str, amount: int) -> TenantQuotaAggregate:
        from dataclasses import replace
        new_usage = {**self.current_usage, resource: self.current_usage.get(resource, 0) + amount}
        return replace(self, current_usage=new_usage, updated_at=datetime.now(timezone.utc))