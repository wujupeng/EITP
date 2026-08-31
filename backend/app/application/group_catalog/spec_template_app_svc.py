"""规格模板应用服务 - 编排规格模板 CRUD 命令，校验集团级/企业级权限。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.group_catalog.aggregates.spec_template_aggregate import (
    AttributeDefinition,
    AttributeType,
    SpecificationTemplateAggregate,
    TemplateLevel,
)
from app.domain.group_catalog.services.group_catalog_permission_checker import (
    GroupCatalogPermissionChecker,
)
from app.domain.shared.entity import EntityId
from app.infrastructure.governance.governance_repositories import (
    SpecTemplateRepository,
)


class SpecTemplateAppSvc:
    """规格模板应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SpecTemplateRepository()

    async def create_template(
        self,
        template_code: str,
        template_name: str,
        attribute_definitions: list[AttributeDefinition],
        template_level: TemplateLevel = TemplateLevel.GROUP,
        tenant_id: UUID | None = None,
    ) -> SpecificationTemplateAggregate:
        GroupCatalogPermissionChecker.enforce_manage()

        agg = SpecificationTemplateAggregate(
            id=EntityId.generate(),
            template_code=template_code,
            template_name=template_name,
            template_level=template_level,
            tenant_id=tenant_id,
            attribute_definitions=attribute_definitions,
        )
        await self._repo.save(self._session, agg)
        return agg

    async def get_template(self, template_id: UUID):
        return await self._repo.get_by_id(self._session, template_id)

    async def list_templates(self, tenant_id: UUID | None = None):
        return await self._repo.list_all(self._session, tenant_id)