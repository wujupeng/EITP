"""版本管理应用服务 - 编排版本查询/对比/回滚命令。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.governance.master_data_version_comparator import (
    MasterDataVersionComparator,
)
from app.domain.shared.entity import EntityId
from app.infrastructure.governance.governance_repositories import (
    MasterDataVersionRepository,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class VersionManagementAppSvc:
    """版本管理应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MasterDataVersionRepository()

    async def list_versions(self, entity_type: str, entity_id: UUID):
        return await self._repo.list_by_entity(self._session, entity_type, entity_id)

    async def compare_versions(self, entity_type: str, entity_id: UUID, version_a: int, version_b: int) -> dict:
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if not ctx.is_authorized("mdm:version:compare"):
            raise MDMError(MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED, "需要版本对比权限")

        versions = await self._repo.list_by_entity(self._session, entity_type, entity_id)
        domain_versions = [self._orm_to_agg(v) for v in versions]
        va = MasterDataVersionComparator.find_version(domain_versions, version_a)
        vb = MasterDataVersionComparator.find_version(domain_versions, version_b)
        return MasterDataVersionComparator.compare(va, vb)

    async def rollback_to_version(self, entity_type: str, entity_id: UUID, target_version: int):
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if not ctx.is_authorized("mdm:version:query"):
            raise MDMError(MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED, "需要版本查询权限")

        versions = await self._repo.list_by_entity(self._session, entity_type, entity_id)
        domain_versions = [self._orm_to_agg(v) for v in versions]
        return MasterDataVersionComparator.rollback_to(domain_versions, target_version)

    def _orm_to_agg(self, orm):
        from app.domain.governance.aggregates.master_data_version_aggregate import (
            ChangeType,
            MasterDataVersionAggregate,
        )
        return MasterDataVersionAggregate(
            id=EntityId(orm.version_id),
            entity_type=orm.entity_type,
            entity_id=orm.entity_id,
            version_number=orm.version_number,
            snapshot_after=orm.snapshot_after,
            change_type=ChangeType(orm.change_type),
            operated_by=orm.operated_by,
            tenant_id=orm.tenant_id,
            snapshot_before=orm.snapshot_before,
            reason=orm.reason,
            operated_at=orm.operated_at,
        )