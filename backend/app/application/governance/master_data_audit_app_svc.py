"""主数据审计应用服务 - 编排审计记录写入与查询。

审计表 append-only（REVOKE UPDATE/DELETE + Trigger 双保险），保留期 ≥365 天。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.audit_entry import AuditAction
from app.domain.audit.master_data_audit_aggregate import MasterDataAuditAggregate
from app.infrastructure.governance.governance_repositories import (
    MasterDataAuditRepository,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class MasterDataAuditAppSvc:
    """主数据审计应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MasterDataAuditRepository()

    async def write_audit(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        tenant_id: UUID | None = None,
        version_number: int | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> MasterDataAuditAggregate:
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        operated_by = ctx.user.user_id

        agg = MasterDataAuditAggregate.create(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=tenant_id,
            version_number=version_number,
            old_value=old_value,
            new_value=new_value,
            operated_by=operated_by,
            reason=reason,
            ip_address=ip_address,
        )
        await self._repo.save(self._session, agg)
        await self._session.flush()
        return agg

    async def list_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        offset: int = 0,
        limit: int = 50,
    ):
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if not ctx.is_authorized("mdm:master_data:query"):
            raise MDMError(MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED, "需要主数据查询权限")

        return await self._repo.list_by_entity(
            self._session, entity_type, entity_id, offset=offset, limit=limit
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ):
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if not ctx.is_authorized("mdm:master_data:query"):
            raise MDMError(MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED, "需要主数据查询权限")
        if ctx.tenant.tenant_id != tenant_id and not ctx.user.is_platform_admin:
            raise MDMError(MDMErrorCode.CROSS_TENANT_POLICY_DENIED, "禁止跨租户查询审计历史")

        return await self._repo.list_by_tenant(
            self._session, tenant_id, offset=offset, limit=limit
        )