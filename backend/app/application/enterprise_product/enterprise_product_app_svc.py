"""企业商品应用服务 - 编排企业商品引用集团商品、解除引用、查询命令。

引用集团商品时自动创建企业商品与企业 SKU，继承集团 SKU 编码/规格/条码/计量单位。
解除引用时标记"引用已解除"保留存量库存。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enterprise_product.aggregates.enterprise_product_aggregate import (
    EnterpriseProductAggregate,
    ReferenceStatus,
)
from app.domain.enterprise_product.entities.enterprise_sku import EnterpriseSku
from app.domain.enterprise_product.services.cross_enterprise_ref_checker import (
    CrossEnterpriseRefChecker,
)
from app.domain.group_catalog.aggregates.group_product_aggregate import (
    GroupProductAggregate,
    GroupProductStatus,
)
from app.domain.shared.entity import EntityId
from app.infrastructure.enterprise_product.enterprise_product_repository import (
    EnterpriseProductRepository,
    EnterpriseSkuRepository,
    ProductReferenceRepository,
)
from app.infrastructure.group_catalog.group_product_repository import (
    GroupProductRepository,
    GroupSkuRepository,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class EnterpriseProductAppSvc:
    """企业商品应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._ep_repo = EnterpriseProductRepository()
        self._esku_repo = EnterpriseSkuRepository()
        self._ref_repo = ProductReferenceRepository()
        self._gp_repo = GroupProductRepository()
        self._gsku_repo = GroupSkuRepository()

    async def reference_group_product(
        self,
        tenant_id: UUID,
        group_product_id: UUID,
        enterprise_product_code: str,
        enterprise_product_name: str | None = None,
        enterprise_category_id: UUID | None = None,
    ) -> EnterpriseProductAggregate:
        """企业引用集团商品 - 自动创建企业商品与企业 SKU。"""
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise MDMError(MDMErrorCode.CROSS_TENANT_POLICY_DENIED, "跨租户操作被拒绝")

        gp_orm = await self._gp_repo.get_by_id(self._session, group_product_id)
        if gp_orm is None:
            raise MDMError(MDMErrorCode.VERSION_NOT_FOUND, f"集团商品 {group_product_id} 不存在")

        gp_agg = GroupProductAggregate(
            id=EntityId(gp_orm.group_product_id),
            group_product_code=gp_orm.group_product_code,
            group_product_name=gp_orm.group_product_name,
            base_unit_id=gp_orm.base_unit_id,
            group_category_id=gp_orm.group_category_id,
            group_brand_id=gp_orm.group_brand_id,
            spec_template_id=gp_orm.spec_template_id,
            description=gp_orm.description,
            status=GroupProductStatus(gp_orm.status),
            published_version=gp_orm.published_version,
        )

        existing_refs = await self._ref_repo.list_by_tenant(self._session, tenant_id)
        ref_tuples = [(r.tenant_id, r.group_product_id) for r in existing_refs]
        CrossEnterpriseRefChecker.validate_reference_creation(gp_agg, tenant_id, ref_tuples)

        existing_ep = await self._ep_repo.get_by_tenant_and_code(
            self._session, tenant_id, enterprise_product_code
        )
        if existing_ep:
            raise MDMError(MDMErrorCode.DUPLICATE_REFERENCE, f"企业商品编码 {enterprise_product_code} 已存在")

        ep_agg = EnterpriseProductAggregate.create_reference(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_code=enterprise_product_code,
            referenced_by=ctx.user.user_id,
            enterprise_product_name=enterprise_product_name or gp_orm.group_product_name,
            enterprise_category_id=enterprise_category_id,
        )
        await self._ep_repo.save(self._session, ep_agg)

        from app.domain.enterprise_product.aggregates.product_reference_aggregate import (
            ProductReferenceAggregate,
        )
        ref_agg = ProductReferenceAggregate.create(
            tenant_id=tenant_id,
            group_product_id=group_product_id,
            enterprise_product_id=ep_agg.id.value,
            referenced_by=ctx.user.user_id,
        )
        await self._ref_repo.save(self._session, ref_agg)

        group_skus = await self._gsku_repo.list_by_product(self._session, group_product_id)
        for gs_orm in group_skus:
            esku = EnterpriseSku(
                enterprise_sku_id=EntityId.generate(),
                tenant_id=tenant_id,
                enterprise_product_id=ep_agg.id,
                group_sku_id=gs_orm.group_sku_id,
                enterprise_sku_code=gs_orm.group_sku_code,
                enterprise_sku_name=gs_orm.group_sku_name,
                enterprise_barcode_list=gs_orm.barcode_list or [],
            )
            await self._esku_repo.save(self._session, esku)

        return ep_agg

    async def release_reference(
        self,
        tenant_id: UUID,
        enterprise_product_id: UUID,
    ) -> EnterpriseProductAggregate:
        """解除引用 - 标记"引用已解除"保留存量库存。"""
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")

        ep_orm = await self._ep_repo.get_by_id(self._session, tenant_id, enterprise_product_id)
        if ep_orm is None:
            raise MDMError(MDMErrorCode.VERSION_NOT_FOUND, f"企业商品 {enterprise_product_id} 不存在")

        ep_agg = EnterpriseProductAggregate(
            id=EntityId(ep_orm.enterprise_product_id),
            tenant_id=ep_orm.tenant_id,
            group_product_id=ep_orm.group_product_id,
            enterprise_product_code=ep_orm.enterprise_product_code,
            enterprise_product_name=ep_orm.enterprise_product_name,
            enterprise_category_id=ep_orm.enterprise_category_id,
            reference_status=ReferenceStatus(ep_orm.reference_status),
            published_version=ep_orm.published_version,
        )
        ep_agg.release_reference(ctx.user.user_id)

        ep_orm.reference_status = ep_agg.reference_status.value
        await self._session.flush()
        return ep_agg

    async def list_enterprise_products(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ):
        return await self._ep_repo.list_by_tenant(self._session, tenant_id, offset, limit)

    async def get_enterprise_product(self, tenant_id: UUID, enterprise_product_id: UUID):
        return await self._ep_repo.get_by_id(self._session, tenant_id, enterprise_product_id)