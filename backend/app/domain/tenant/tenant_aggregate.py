"""租户聚合根 - 状态机受控，封装开通/停用/注销/迁移行为。"""

from __future__ import annotations

from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.tenant.tenant_events import (
    TenantDeprovisionedEvent,
    TenantDisabledEvent,
    TenantProvisionFailedEvent,
    TenantProvisionedEvent,
)
from app.domain.tenant.tenant_state import (
    DataPlacement,
    TenantStatus,
    VALID_TRANSITIONS,
)
from app.interfaces.middleware.error_handler import (
    DomainError,
    ErrorCode,
)


class TenantAggregate(AggregateRoot):
    """租户聚合根 - 管理租户生命周期与状态机一致性。

    状态机：开通中 → 正常 → 停用 → 注销
    异常路径：开通中 → 开通失败 → (重试) 开通中
    """

    def __init__(
        self,
        id: EntityId,
        enterprise_name: str,
        idempotency_key: str,
        status: TenantStatus = TenantStatus.PROVISIONING,
        data_placement: DataPlacement = DataPlacement.SHARED_DB,
        version: int = 1,
    ) -> None:
        super().__init__(id)
        self._enterprise_name = enterprise_name
        self._idempotency_key = idempotency_key
        self._status = status
        self._data_placement = data_placement
        self._version = version

    @property
    def enterprise_name(self) -> str:
        return self._enterprise_name

    @property
    def idempotency_key(self) -> str:
        return self._idempotency_key

    @property
    def status(self) -> TenantStatus:
        return self._status

    @property
    def data_placement(self) -> DataPlacement:
        return self._data_placement

    @property
    def version(self) -> int:
        return self._version

    def _transition_to(self, target: TenantStatus) -> None:
        if target not in VALID_TRANSITIONS.get(self._status, set()):
            raise DomainError(
                ErrorCode.DEPROVISION_REQUIRES_DISABLE,
                f"非法状态流转: {self._status.value} → {target.value}",
            )
        self._status = target
        self._touch()

    def provision(self) -> None:
        """完成开通：provisioning → active。"""
        self._transition_to(TenantStatus.ACTIVE)
        self._record_event(
            TenantProvisionedEvent(
                tenant_id=self._id.value,
                enterprise_name=self._enterprise_name,
            )
        )

    def mark_failed(self, reason: str) -> None:
        """标记开通失败：provisioning → failed。"""
        self._transition_to(TenantStatus.FAILED)
        self._record_event(
            TenantProvisionFailedEvent(
                tenant_id=self._id.value,
                reason=reason,
            )
        )

    def retry_provision(self) -> None:
        """重试开通：failed → provisioning。"""
        self._transition_to(TenantStatus.PROVISIONING)

    def disable(self) -> None:
        """停用租户：active → disabled。"""
        self._transition_to(TenantStatus.DISABLED)
        self._record_event(
            TenantDisabledEvent(tenant_id=self._id.value)
        )

    def enable(self) -> None:
        """恢复租户：disabled → active。"""
        self._transition_to(TenantStatus.ACTIVE)

    def deprovision(self, confirm_token: str | None = None) -> None:
        """注销租户：disabled → deprovisioned，需二次确认。

        Args:
            confirm_token: 确认令牌，必须与租户 ID 字符串匹配

        Raises:
            DomainError: 未提供确认令牌或令牌不匹配
        """
        if confirm_token is None:
            raise DomainError(
                ErrorCode.DEPROVISION_CONFIRM_REQUIRED,
                "注销需要二次确认令牌",
            )
        if confirm_token != str(self._id.value):
            raise DomainError(
                ErrorCode.DEPROVISION_CONFIRM_REQUIRED,
                "确认令牌不匹配",
            )
        self._transition_to(TenantStatus.DEPROVISIONED)
        self._record_event(
            TenantDeprovisionedEvent(tenant_id=self._id.value)
        )

    def migrate_to(self, target_placement: DataPlacement) -> None:
        """迁移数据放置模式。"""
        if self._status != TenantStatus.ACTIVE:
            raise DomainError(
                ErrorCode.MIGRATION_IN_PROGRESS,
                "仅活跃租户可迁移数据放置模式",
            )
        self._data_placement = target_placement
        self._version += 1
        self._touch()