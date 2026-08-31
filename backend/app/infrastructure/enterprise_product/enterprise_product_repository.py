"""企业商品与引用关系仓储 - 企业级表含 tenant_id，应用 TenantFilterEvent。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.mdm.models import (
    EnterpriseCategoryORM,
    EnterpriseProductORM,
    EnterpriseSkuORM,
    ProductCustomizationORM,
    ProductReferenceORM,
)


class EnterpriseProductRepository:
    """企业商品仓储。"""

    async def save(self, session: AsyncSession, agg) -> EnterpriseProductORM:
        orm = EnterpriseProductORM(
            enterprise_product_id=agg.id.value,
            tenant_id=agg.tenant_id,
            group_product_id=agg.group_product_id,
            enterprise_product_code=agg.enterprise_product_code,
            enterprise_product_name=agg.enterprise_product_name,
            enterprise_category_id=agg.enterprise_category_id,
            reference_status=agg.reference_status.value,
            published_version=agg.published_version,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, enterprise_product_id: UUID) -> EnterpriseProductORM | None:
        stmt = select(EnterpriseProductORM).where(
            EnterpriseProductORM.tenant_id == tenant_id,
            EnterpriseProductORM.enterprise_product_id == enterprise_product_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_tenant_and_code(self, session: AsyncSession, tenant_id: UUID, code: str) -> EnterpriseProductORM | None:
        stmt = select(EnterpriseProductORM).where(
            EnterpriseProductORM.tenant_id == tenant_id,
            EnterpriseProductORM.enterprise_product_code == code,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID, offset: int = 0, limit: int = 50) -> list[EnterpriseProductORM]:
        stmt = select(EnterpriseProductORM).where(
            EnterpriseProductORM.tenant_id == tenant_id,
        ).offset(offset).limit(limit)
        return list((await session.execute(stmt)).scalars().all())


class EnterpriseSkuRepository:
    """企业 SKU 仓储。"""

    async def save(self, session: AsyncSession, sku) -> EnterpriseSkuORM:
        orm = EnterpriseSkuORM(
            enterprise_sku_id=sku.enterprise_sku_id.value,
            tenant_id=sku.tenant_id,
            enterprise_product_id=sku.enterprise_product_id.value,
            group_sku_id=sku.group_sku_id,
            enterprise_sku_code=sku.enterprise_sku_code,
            enterprise_sku_name=sku.enterprise_sku_name,
            enterprise_barcode_list=sku.enterprise_barcode_list,
            status=sku.status.value,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, enterprise_sku_id: UUID) -> EnterpriseSkuORM | None:
        stmt = select(EnterpriseSkuORM).where(
            EnterpriseSkuORM.tenant_id == tenant_id,
            EnterpriseSkuORM.enterprise_sku_id == enterprise_sku_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_product(self, session: AsyncSession, tenant_id: UUID, enterprise_product_id: UUID) -> list[EnterpriseSkuORM]:
        stmt = select(EnterpriseSkuORM).where(
            EnterpriseSkuORM.tenant_id == tenant_id,
            EnterpriseSkuORM.enterprise_product_id == enterprise_product_id,
        )
        return list((await session.execute(stmt)).scalars().all())


class ProductReferenceRepository:
    """商品引用关系仓储 - 复合唯一约束 (tenant_id, group_product_id)。"""

    async def save(self, session: AsyncSession, agg) -> ProductReferenceORM:
        orm = ProductReferenceORM(
            reference_id=agg.id.value,
            tenant_id=agg.tenant_id,
            group_product_id=agg.group_product_id,
            enterprise_product_id=agg.enterprise_product_id,
            referenced_by=agg.referenced_by,
            referenced_at=agg.referenced_at,
            reference_status=agg.reference_status.value,
            released_by=agg.released_by,
            released_at=agg.released_at,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, reference_id: UUID) -> ProductReferenceORM | None:
        stmt = select(ProductReferenceORM).where(ProductReferenceORM.reference_id == reference_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID) -> list[ProductReferenceORM]:
        stmt = select(ProductReferenceORM).where(ProductReferenceORM.tenant_id == tenant_id)
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_group_product(self, session: AsyncSession, group_product_id: UUID) -> list[ProductReferenceORM]:
        stmt = select(ProductReferenceORM).where(ProductReferenceORM.group_product_id == group_product_id)
        return list((await session.execute(stmt)).scalars().all())

    async def find_existing(self, session: AsyncSession, tenant_id: UUID, group_product_id: UUID) -> ProductReferenceORM | None:
        stmt = select(ProductReferenceORM).where(
            ProductReferenceORM.tenant_id == tenant_id,
            ProductReferenceORM.group_product_id == group_product_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()


class ProductCustomizationRepository:
    """商品定制仓储。"""

    async def save(self, session: AsyncSession, agg) -> ProductCustomizationORM:
        orm = ProductCustomizationORM(
            customization_id=agg.id.value,
            tenant_id=agg.tenant_id,
            enterprise_product_id=agg.enterprise_product_id,
            enterprise_sku_id=agg.enterprise_sku_id,
            sales_price=agg.sales_price,
            purchase_price=agg.purchase_price,
            inventory_strategy=agg.inventory_strategy.value if agg.inventory_strategy else None,
            safety_stock=agg.safety_stock,
            cost_model=agg.cost_model.value if agg.cost_model else None,
            custom_attributes=agg.custom_attributes,
            version=agg.version,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, customization_id: UUID) -> ProductCustomizationORM | None:
        stmt = select(ProductCustomizationORM).where(
            ProductCustomizationORM.tenant_id == tenant_id,
            ProductCustomizationORM.customization_id == customization_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_product(self, session: AsyncSession, tenant_id: UUID, enterprise_product_id: UUID) -> ProductCustomizationORM | None:
        stmt = select(ProductCustomizationORM).where(
            ProductCustomizationORM.tenant_id == tenant_id,
            ProductCustomizationORM.enterprise_product_id == enterprise_product_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()


class EnterpriseCategoryRepository:
    """企业分类仓储。"""

    async def save(self, session: AsyncSession, agg) -> EnterpriseCategoryORM:
        orm = EnterpriseCategoryORM(
            enterprise_category_id=agg.id.value,
            tenant_id=agg.tenant_id,
            enterprise_category_code=agg.enterprise_category_code,
            enterprise_category_name=agg.enterprise_category_name,
            parent_category_id=agg.parent_category_id,
            parent_category_level=agg.parent_category_level.value if agg.parent_category_level else None,
            level=agg.level,
            status=agg.status.value,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, enterprise_category_id: UUID) -> EnterpriseCategoryORM | None:
        stmt = select(EnterpriseCategoryORM).where(
            EnterpriseCategoryORM.tenant_id == tenant_id,
            EnterpriseCategoryORM.enterprise_category_id == enterprise_category_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID) -> list[EnterpriseCategoryORM]:
        stmt = select(EnterpriseCategoryORM).where(
            EnterpriseCategoryORM.tenant_id == tenant_id,
        ).order_by(EnterpriseCategoryORM.level)
        return list((await session.execute(stmt)).scalars().all())
