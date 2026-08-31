"""负库存策略审计写入器 - 策略变更时强制写入审计记录。

- 策略变更与审计写入在同一数据库事务内原子完成（spec 5.9.1.4/5.9.1.9）
- 原因必填校验（spec 5.9.1.5）
- 无审计的策略变更被拒绝
- 权限控制：仅租户管理员可配置，业务用户/跨租户修改被拒绝（spec 5.9.1.3）
"""

from __future__ import annotations

from uuid import UUID

from app.domain.governance.aggregates.negative_inventory_policy_audit_aggregate import (
    NegativeInventoryPolicyAuditAggregate,
    NegativePolicyMode,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class NegativeInventoryPolicyAuditWriter:
    """负库存策略审计写入器。"""

    POLICY_CONFIG_PERMISSION = "mdm:negative_policy:config"

    @classmethod
    def enforce_permission(cls, tenant_id: UUID) -> None:
        """权限控制（spec 5.9.1.3）。

        - 仅允许租户管理员配置本租户负库存策略
        - 业务用户修改被拒绝（EITP_MDM_NEGATIVE_POLICY_PERMISSION_DENIED）
        - 跨租户修改被拒绝（EITP_MDM_CROSS_TENANT_POLICY_DENIED）
        - 由 tenant_id 列 + RLS 策略 + TenantFilterEvent 三层防护
        """
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(
                MDMErrorCode.NEGATIVE_POLICY_PERMISSION_DENIED,
                "未认证，缺少安全上下文",
            )

        if ctx.tenant.tenant_id != tenant_id:
            raise MDMError(
                MDMErrorCode.CROSS_TENANT_POLICY_DENIED,
                "禁止跨租户修改负库存策略",
            )

        if not ctx.is_authorized(cls.POLICY_CONFIG_PERMISSION):
            raise MDMError(
                MDMErrorCode.NEGATIVE_POLICY_PERMISSION_DENIED,
                "仅租户管理员可配置负库存策略",
            )

    @staticmethod
    def write_audit(
        tenant_id: UUID,
        policy_before: NegativePolicyMode,
        policy_after: NegativePolicyMode,
        operated_by: UUID,
        reason: str,
    ) -> NegativeInventoryPolicyAuditAggregate:
        """写入策略变更审计记录。

        策略更新与审计写入在同一数据库事务内原子完成（spec 5.9.1.4/5.9.1.9）。
        实际事务管理由调用方通过 Unit of Work 模式控制。
        """
        if policy_before == policy_after:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                "策略未发生变化，无需写入审计",
            )

        return NegativeInventoryPolicyAuditAggregate.create(
            tenant_id=tenant_id,
            policy_before=policy_before,
            policy_after=policy_after,
            operated_by=operated_by,
            reason=reason,
        )

    @classmethod
    def change_policy_with_audit(
        cls,
        tenant_id: UUID,
        policy_before: NegativePolicyMode,
        policy_after: NegativePolicyMode,
        operated_by: UUID,
        reason: str,
    ) -> NegativeInventoryPolicyAuditAggregate:
        """策略变更并写入审计（权限校验 + 审计写入原子完成）。

        无审计的策略变更被拒绝。
        """
        cls.enforce_permission(tenant_id)
        return cls.write_audit(
            tenant_id=tenant_id,
            policy_before=policy_before,
            policy_after=policy_after,
            operated_by=operated_by,
            reason=reason,
        )