"""负库存策略审计聚合根 - 策略变更审计，不可篡改，仅追加。

写入后不可修改不可删除（spec 5.9.1.4，append-only + REVOKE UPDATE/DELETE + Trigger 双保险）。
保留期 ≥365 天。reason 不可空。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class NegativePolicyMode(str, Enum):
    STRICT = "strict"
    ALLOW = "allow"
    WARNING = "warning"
    APPROVAL = "approval"


class NegativeInventoryPolicyAuditAggregate:
    """负库存策略审计聚合根 - 不可变，仅追加。

    每条记录包含：审计 ID、租户 ID、变更前策略、变更后策略、操作人、操作时间、原因。
    reason 不可空（spec 5.9.1.5）。
    """

    def __init__(
        self,
        audit_id: UUID,
        tenant_id: UUID,
        policy_before: NegativePolicyMode,
        policy_after: NegativePolicyMode,
        operated_by: UUID,
        reason: str,
        operated_at: datetime | None = None,
    ) -> None:
        if not reason or not reason.strip():
            raise MDMError(
                MDMErrorCode.NEGATIVE_POLICY_REASON_REQUIRED,
                "负库存策略变更原因不能为空",
            )
        self._audit_id = audit_id
        self._tenant_id = tenant_id
        self._policy_before = policy_before
        self._policy_after = policy_after
        self._operated_by = operated_by
        self._reason = reason
        self._operated_at = operated_at or datetime.now(timezone.utc)

    @property
    def audit_id(self) -> UUID:
        return self._audit_id

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def policy_before(self) -> NegativePolicyMode:
        return self._policy_before

    @property
    def policy_after(self) -> NegativePolicyMode:
        return self._policy_after

    @property
    def operated_by(self) -> UUID:
        return self._operated_by

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def operated_at(self) -> datetime:
        return self._operated_at

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        policy_before: NegativePolicyMode,
        policy_after: NegativePolicyMode,
        operated_by: UUID,
        reason: str,
    ) -> NegativeInventoryPolicyAuditAggregate:
        """创建负库存策略审计记录。"""
        return cls(
            audit_id=uuid4(),
            tenant_id=tenant_id,
            policy_before=policy_before,
            policy_after=policy_after,
            operated_by=operated_by,
            reason=reason,
        )

    @staticmethod
    def validate_default_must_strict(
        policy: NegativePolicyMode,
        is_new_tenant: bool = True,
    ) -> None:
        """校验默认策略必须 STRICT（spec 5.9.1.1/5.9.1.8）。

        新租户初始化时强制设置默认负库存策略为 STRICT（global_forbidden）。
        """
        if is_new_tenant and policy != NegativePolicyMode.STRICT:
            raise MDMError(
                MDMErrorCode.NEGATIVE_POLICY_DEFAULT_MUST_STRICT,
                f"新租户默认负库存策略必须为 STRICT，当前为 {policy.value}",
            )