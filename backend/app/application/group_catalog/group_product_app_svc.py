"""集团商品目录应用服务 - 编排集团商品/SKU/分类/品牌/单位 CRUD 命令。

校验集团级权限（mdm:group_product:manage 平台级角色）。
集团商品变更经治理工作流审批发布后生效（spec 5.1.1.8）。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.group_catalog.aggregates.group_product_aggregate import (
    GroupProductAggregate,
    GroupProductStatus,
)
from app.domain.group_catalog.entities.group_sku import GroupSku
from app.domain.group_catalog.services.group_catalog_permission_checker import (
    GroupCatalogPermissionChecker,
)
from app.domain.shared.entity import EntityId
from app.infrastructure.group_catalog.group_product_repository import (
    GroupBrandRepository,
    GroupCategoryRepository,
    GroupProductRepository,
    GroupSkuRepository,
    GroupUnitRepository,
)


class GroupProductAppSvc:
    """集团商品目录应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._product_repo = GroupProductRepository()
        self._sku_repo = GroupSkuRepository()
        self._category_repo = GroupCategoryRepository()
        self._brand_repo = GroupBrandRepository()
        self._unit_repo = GroupUnitRepository()

    async def create_group_product(
        self,
        group_product_code: str,
        group_product_name: str,
        base_unit_id: UUID,
        group_category_id: UUID | None = None,
        group_brand_id: UUID | None = None,
        spec_template_id: UUID | None = None,
        description: str | None = None,
    ) -> GroupProductAggregate:
        GroupCatalogPermissionChecker.enforce_manage()

        existing = await self._product_repo.get_by_code(self._session, group_product_code)
        if existing:
            from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
            raise MDMError(MDMErrorCode.GROUP_SKU_DUPLICATE, f"集团商品编码 {group_product_code} 已存在")

        agg = GroupProductAggregate(
            id=EntityId.generate(),
            group_product_code=group_product_code,
            group_product_name=group_product_name,
            base_unit_id=base_unit_id,
            group_category_id=group_category_id,
            group_brand_id=group_brand_id,
            spec_template_id=spec_template_id,
            description=description,
        )
        await self._product_repo.save(self._session, agg)
        return agg

    async def get_group_product(self, group_product_id: UUID):
        return await self._product_repo.get_by_id(self._session, group_product_id)

    async def list_group_products(self, offset: int = 0, limit: int = 50) -> list:
        return await self._product_repo.list_all(self._session, offset, limit)

    async def disable_group_product(self, group_product_id: UUID) -> GroupProductAggregate:
        GroupCatalogPermissionChecker.enforce_manage()

        orm = await self._product_repo.get_by_id(self._session, group_product_id)
        if orm is None:
            from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
            raise MDMError(MDMErrorCode.VERSION_NOT_FOUND, f"集团商品 {group_product_id} 不存在")

        agg = GroupProductAggregate(
            id=EntityId(orm.group_product_id),
            group_product_code=orm.group_product_code,
            group_product_name=orm.group_product_name,
            base_unit_id=orm.base_unit_id,
            group_category_id=orm.group_category_id,
            group_brand_id=orm.group_brand_id,
            spec_template_id=orm.spec_template_id,
            description=orm.description,
            status=GroupProductStatus(orm.status),
            published_version=orm.published_version,
        )

        refs = await self._check_active_references(group_product_id)
        if refs:
            agg.mark_has_active_references()

        agg.disable()
        await self._product_repo.update(self._session, agg)
        return agg

    async def _check_active_references(self, group_product_id: UUID) -> bool:
        from sqlalchemy import select
        from app.infrastructure.mdm.models import ProductReferenceORM
        stmt = select(ProductReferenceORM).where(
            ProductReferenceORM.group_product_id == group_product_id,
            ProductReferenceORM.reference_status == "active",
        ).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add_group_sku(
        self,
        group_product_id: UUID,
        group_sku_code: str,
        group_sku_name: str,
        unit_id: UUID,
        specification_instance: dict | None = None,
        barcode_list: list[str] | None = None,
        weight: float | None = None,
        volume: float | None = None,
    ) -> GroupSku:
        GroupCatalogPermissionChecker.enforce_manage()

        existing = await self._sku_repo.get_by_code(self._session, group_sku_code)
        if existing:
            from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
            raise MDMError(MDMErrorCode.GROUP_SKU_DUPLICATE, f"集团 SKU 编码 {group_sku_code} 已存在")

        sku = GroupSku(
            group_sku_id=EntityId.generate(),
            group_product_id=EntityId(group_product_id),
            group_sku_code=group_sku_code,
            group_sku_name=group_sku_name,
            unit_id=unit_id,
            specification_instance=specification_instance,
            barcode_list=barcode_list,
            weight=weight,
            volume=volume,
        )
        await self._sku_repo.save(self._session, sku)
        return sku

    async def list_group_skus(self, group_product_id: UUID) -> list:
        return await self._sku_repo.list_by_product(self._session, group_product_id)