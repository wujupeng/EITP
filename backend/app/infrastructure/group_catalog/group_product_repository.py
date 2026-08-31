"""集团商品目录仓储 - GroupProduct/GroupSku/GroupCategory/GroupBrand/GroupUnit 持久化。

集团级表无 tenant_id，不应用 TenantFilterEvent。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.group_catalog.aggregates.group_product_aggregate import (
    GroupProductAggregate,
    GroupProductStatus,
)
from app.domain.group_catalog.entities.group_sku import GroupSku, GroupSkuStatus
from app.domain.shared.entity import EntityId
from app.infrastructure.mdm.models import (
    GroupBrandORM,
    GroupCategoryORM,
    GroupProductORM,
    GroupSkuORM,
    GroupUnitConversionORM,
    GroupUnitORM,
)


class GroupProductRepository:
    """集团商品仓储。"""

    async def save(self, session: AsyncSession, agg: GroupProductAggregate) -> GroupProductORM:
        orm = GroupProductORM(
            group_product_id=agg.id.value,
            group_product_code=agg.group_product_code,
            group_product_name=agg.group_product_name,
            group_category_id=agg.group_category_id,
            group_brand_id=agg.group_brand_id,
            base_unit_id=agg.base_unit_id,
            spec_template_id=agg.spec_template_id,
            status=agg.status.value,
            published_version=agg.published_version,
            description=agg.description,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, group_product_id: UUID) -> GroupProductORM | None:
        stmt = select(GroupProductORM).where(GroupProductORM.group_product_id == group_product_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, session: AsyncSession, code: str) -> GroupProductORM | None:
        stmt = select(GroupProductORM).where(GroupProductORM.group_product_code == code)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_all(self, session: AsyncSession, offset: int = 0, limit: int = 50) -> list[GroupProductORM]:
        stmt = select(GroupProductORM).offset(offset).limit(limit)
        return list((await session.execute(stmt)).scalars().all())

    async def update(self, session: AsyncSession, agg: GroupProductAggregate) -> GroupProductORM | None:
        orm = await self.get_by_id(session, agg.id.value)
        if orm is None:
            return None
        orm.group_product_name = agg.group_product_name
        orm.group_category_id = agg.group_category_id
        orm.group_brand_id = agg.group_brand_id
        orm.spec_template_id = agg.spec_template_id
        orm.status = agg.status.value
        orm.published_version = agg.published_version
        orm.description = agg.description
        await session.flush()
        return orm


class GroupSkuRepository:
    """集团 SKU 仓储。"""

    async def save(self, session: AsyncSession, sku: GroupSku) -> GroupSkuORM:
        orm = GroupSkuORM(
            group_sku_id=sku.group_sku_id.value,
            group_product_id=sku.group_product_id.value,
            group_sku_code=sku.group_sku_code,
            group_sku_name=sku.group_sku_name,
            specification_instance=sku.specification_instance,
            barcode_list=sku.barcode_list,
            unit_id=sku.unit_id,
            weight=sku.weight,
            volume=sku.volume,
            status=sku.status.value,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, group_sku_id: UUID) -> GroupSkuORM | None:
        stmt = select(GroupSkuORM).where(GroupSkuORM.group_sku_id == group_sku_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, session: AsyncSession, code: str) -> GroupSkuORM | None:
        stmt = select(GroupSkuORM).where(GroupSkuORM.group_sku_code == code)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_product(self, session: AsyncSession, group_product_id: UUID) -> list[GroupSkuORM]:
        stmt = select(GroupSkuORM).where(GroupSkuORM.group_product_id == group_product_id)
        return list((await session.execute(stmt)).scalars().all())


class GroupCategoryRepository:
    """集团分类仓储。"""

    async def save(self, session: AsyncSession, agg) -> GroupCategoryORM:
        orm = GroupCategoryORM(
            group_category_id=agg.id.value,
            group_category_code=agg.group_category_code,
            group_category_name=agg.group_category_name,
            parent_category_id=agg.parent_category_id,
            level=agg.level,
            status=agg.status.value,
            published_version=agg.published_version,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, group_category_id: UUID) -> GroupCategoryORM | None:
        stmt = select(GroupCategoryORM).where(GroupCategoryORM.group_category_id == group_category_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, session: AsyncSession, code: str) -> GroupCategoryORM | None:
        stmt = select(GroupCategoryORM).where(GroupCategoryORM.group_category_code == code)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_tree(self, session: AsyncSession) -> list[GroupCategoryORM]:
        stmt = select(GroupCategoryORM).order_by(GroupCategoryORM.level)
        return list((await session.execute(stmt)).scalars().all())


class GroupBrandRepository:
    """集团品牌仓储。"""

    async def save(self, session: AsyncSession, brand) -> GroupBrandORM:
        orm = GroupBrandORM(
            group_brand_id=brand.group_brand_id.value,
            group_brand_code=brand.group_brand_code,
            group_brand_name=brand.group_brand_name,
            status=brand.status.value,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, group_brand_id: UUID) -> GroupBrandORM | None:
        stmt = select(GroupBrandORM).where(GroupBrandORM.group_brand_id == group_brand_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_all(self, session: AsyncSession) -> list[GroupBrandORM]:
        stmt = select(GroupBrandORM)
        return list((await session.execute(stmt)).scalars().all())


class GroupUnitRepository:
    """集团单位仓储。"""

    async def save(self, session: AsyncSession, unit) -> GroupUnitORM:
        orm = GroupUnitORM(
            group_unit_id=unit.group_unit_id.value,
            group_unit_code=unit.group_unit_code,
            group_unit_name=unit.group_unit_name,
            is_base_unit=unit.is_base_unit,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, group_unit_id: UUID) -> GroupUnitORM | None:
        stmt = select(GroupUnitORM).where(GroupUnitORM.group_unit_id == group_unit_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_all(self, session: AsyncSession) -> list[GroupUnitORM]:
        stmt = select(GroupUnitORM)
        return list((await session.execute(stmt)).scalars().all())

    async def save_conversion(self, session: AsyncSession, conversion) -> GroupUnitConversionORM:
        orm = GroupUnitConversionORM(
            conversion_id=conversion.conversion_id,
            from_unit_id=conversion.from_unit_id,
            to_unit_id=conversion.to_unit_id,
            ratio=conversion.ratio,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def list_conversions(self, session: AsyncSession) -> list[GroupUnitConversionORM]:
        stmt = select(GroupUnitConversionORM)
        return list((await session.execute(stmt)).scalars().all())