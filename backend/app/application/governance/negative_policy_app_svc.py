"""负库存策略应用服务 - 编排策略查询/变更/审计历史命令。

策略更新（inv_negative_stock_policy）与审计写入（mdm_negative_inventory_policy_audit）
在同一数据库事务内原子完成（spec 5.9.1.4/5.9.1.9）。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.governance.negative_inventory_policy_audit_writer import (
    NegativeInventoryPolicyAuditWriter,
)
from app.domain.governance.aggregates.negative_inventory_policy_audit_aggregate import (
    NegativeInventoryPolicyAuditAggregate,
    NegativePolicyMode,
)
from app.infrastructure.governance.governance_repositories import (
    NegativeInventoryPolicyAuditRepository,
)
from app.infrastructure.inventory.models import NegativeStockPolicyORM
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


_MDM_TO_INV_MODE: dict[NegativePolicyMode, str] = {
    NegativePolicyMode.STRICT: "global_forbid",
    NegativePolicyMode.ALLOW: "global_allow",
    NegativePolicyMode.WARNING: "by_business",
    NegativePolicyMode.APPROVAL: "require_approval",
}

_INV_TO_MDM_MODE: dict[str, NegativePolicyMode] = {
    "global_forbid": NegativePolicyMode.STRICT,
    "global_allow": NegativePolicyMode.ALLOW,
    "by_business": NegativePolicyMode.WARNING,
    "by_warehouse": NegativePolicyMode.WARNING,
    "require_approval": NegativePolicyMode.APPROVAL,
}


class NegativePolicyAppSvc:
    """负库存策略应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit_repo = NegativeInventoryPolicyAuditRepository()

    async def get_current_policy(self, tenant_id: UUID) -> NegativePolicyMode:
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if ctx.tenant.tenant_id != tenant_id and not ctx.user.is_platform_admin:
            raise MDMError(MDMErrorCode.CROSS_TENANT_POLICY_DENIED, "禁止跨租户查询负库存策略")

        orm = await self._load_policy(tenant_id)
        if orm is None:
            return NegativePolicyMode.STRICT
        return _INV_TO_MDM_MODE.get(orm.mode, NegativePolicyMode.STRICT)

    async def change_policy(
        self,
        tenant_id: UUID,
        new_policy: NegativePolicyMode,
        reason: str,
    ) -> NegativeInventoryPolicyAuditAggregate:
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        operated_by = ctx.user.user_id

        orm = await self._load_policy(tenant_id)
        if orm is None:
            policy_before = NegativePolicyMode.STRICT
            orm = NegativeStockPolicyORM(
                tenant_id=tenant_id,
                mode=_MDM_TO_INV_MODE[new_policy],
            )
            self._session.add(orm)
        else:
            policy_before = _INV_TO_MDM_MODE.get(orm.mode, NegativePolicyMode.STRICT)
            orm.mode = _MDM_TO_INV_MODE[new_policy]

        audit_agg = NegativeInventoryPolicyAuditWriter.change_policy_with_audit(
            tenant_id=tenant_id,
            policy_before=policy_before,
            policy_after=new_policy,
            operated_by=operated_by,
            reason=reason,
        )
        await self._audit_repo.save(self._session, audit_agg)
        await self._session.flush()
        return audit_agg

    async def initialize_default_policy(self, tenant_id: UUID) -> None:
        """新租户初始化默认 STRICT 策略（spec 5.9.1.1/5.9.1.8）。"""
        NegativeInventoryPolicyAuditAggregate.validate_default_must_strict(
            NegativePolicyMode.STRICT, is_new_tenant=True
        )
        existing = await self._load_policy(tenant_id)
        if existing is not None:
            return
        orm = NegativeStockPolicyORM(
            tenant_id=tenant_id,
            mode=_MDM_TO_INV_MODE[NegativePolicyMode.STRICT],
        )
        self._session.add(orm)
        await self._session.flush()

    async def list_audit_history(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ):
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if not ctx.is_authorized("mdm:negative_policy:audit:query"):
            raise MDMError(MDMErrorCode.NEGATIVE_POLICY_PERMISSION_DENIED, "需要审计查询权限")
        if ctx.tenant.tenant_id != tenant_id and not ctx.user.is_platform_admin:
            raise MDMError(MDMErrorCode.CROSS_TENANT_POLICY_DENIED, "禁止跨租户查询审计历史")

        return await self._audit_repo.list_by_tenant(
            self._session, tenant_id, offset=offset, limit=limit
        )

    async def _load_policy(self, tenant_id: UUID) -> NegativeStockPolicyORM | None:
        stmt = select(NegativeStockPolicyORM).where(
            NegativeStockPolicyORM.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()