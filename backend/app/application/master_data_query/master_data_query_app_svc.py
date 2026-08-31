"""主数据统一查询应用服务 - 按企业商品标识返回完整主数据含定制信息。

为采购、销售、仓储、核算等下游业务 Bounded Context 提供统一商品主数据查询接口。
使用 Redis 缓存（TTL=300s），Redis 故障时降级为数据库查询（性能下降但功能不丢）。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.master_data_query.master_data_query_redis_store import (
    MasterDataQueryRedisStore,
)
from app.infrastructure.mdm.models import (
    EnterpriseProductORM,
    EnterpriseSkuORM,
    GroupProductORM,
    GroupSkuORM,
    ProductCustomizationORM,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class MasterDataQueryAppSvc:
    """主数据统一查询应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_master_data(self, tenant_id: UUID, enterprise_product_id: UUID) -> dict:
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if not ctx.is_authorized("mdm:master_data:query"):
            raise MDMError(MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED, "需要主数据查询权限")

        cache = await MasterDataQueryRedisStore.get_enterprise_product_cache(
            tenant_id, {"enterprise_product_id": str(enterprise_product_id)}
        )
        if cache is not None:
            return cache[0] if cache else {}

        ep = await self._load_enterprise_product(tenant_id, enterprise_product_id)
        if ep is None:
            raise MDMError(MDMErrorCode.PRODUCT_NOT_AVAILABLE, "企业商品不存在")
        if ep.reference_status != "active":
            raise MDMError(MDMErrorCode.PRODUCT_NOT_AVAILABLE, "商品已停用或引用已解除")

        gp = await self._load_group_product(ep.group_product_id)
        skus = await self._load_enterprise_skus(tenant_id, enterprise_product_id)
        group_skus = await self._load_group_skus(ep.group_product_id)
        customization = await self._load_customization(tenant_id, enterprise_product_id)

        result = {
            "enterprise_product": self._ep_to_dict(ep),
            "group_product": self._gp_to_dict(gp) if gp else None,
            "enterprise_skus": [self._esku_to_dict(s) for s in skus],
            "group_skus": [self._gsku_to_dict(s) for s in group_skus],
            "customization": self._cust_to_dict(customization) if customization else None,
        }

        await MasterDataQueryRedisStore.set_enterprise_product_cache(
            tenant_id, {"enterprise_product_id": str(enterprise_product_id)}, [result]
        )
        return result

    async def query_by_filter(self, tenant_id: UUID, filter_dict: dict) -> list[dict]:
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if not ctx.is_authorized("mdm:master_data:query"):
            raise MDMError(MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED, "需要主数据查询权限")

        cache = await MasterDataQueryRedisStore.get_enterprise_product_cache(tenant_id, filter_dict)
        if cache is not None:
            return cache

        stmt = select(EnterpriseProductORM).where(
            EnterpriseProductORM.tenant_id == tenant_id,
            EnterpriseProductORM.reference_status == "active",
        )
        if "enterprise_product_code" in filter_dict:
            stmt = stmt.where(
                EnterpriseProductORM.enterprise_product_code == filter_dict["enterprise_product_code"]
            )
        if "group_product_id" in filter_dict:
            stmt = stmt.where(
                EnterpriseProductORM.group_product_id == UUID(filter_dict["group_product_id"])
            )
        limit = filter_dict.get("limit", 50)
        stmt = stmt.limit(limit)

        eps = list((await self._session.execute(stmt)).scalars().all())
        results = [self._ep_to_dict(ep) for ep in eps]

        await MasterDataQueryRedisStore.set_enterprise_product_cache(tenant_id, filter_dict, results)
        return results

    async def _load_enterprise_product(self, tenant_id: UUID, ep_id: UUID) -> EnterpriseProductORM | None:
        stmt = select(EnterpriseProductORM).where(
            EnterpriseProductORM.tenant_id == tenant_id,
            EnterpriseProductORM.enterprise_product_id == ep_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def _load_group_product(self, gp_id: UUID) -> GroupProductORM | None:
        stmt = select(GroupProductORM).where(GroupProductORM.group_product_id == gp_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def _load_enterprise_skus(self, tenant_id: UUID, ep_id: UUID) -> list[EnterpriseSkuORM]:
        stmt = select(EnterpriseSkuORM).where(
            EnterpriseSkuORM.tenant_id == tenant_id,
            EnterpriseSkuORM.enterprise_product_id == ep_id,
            EnterpriseSkuORM.status == "active",
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def _load_group_skus(self, gp_id: UUID) -> list[GroupSkuORM]:
        stmt = select(GroupSkuORM).where(
            GroupSkuORM.group_product_id == gp_id,
            GroupSkuORM.status == "active",
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def _load_customization(self, tenant_id: UUID, ep_id: UUID) -> ProductCustomizationORM | None:
        stmt = select(ProductCustomizationORM).where(
            ProductCustomizationORM.tenant_id == tenant_id,
            ProductCustomizationORM.enterprise_product_id == ep_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def _ep_to_dict(ep: EnterpriseProductORM) -> dict:
        return {
            "enterprise_product_id": str(ep.enterprise_product_id),
            "enterprise_product_code": ep.enterprise_product_code,
            "enterprise_product_name": ep.enterprise_product_name,
            "group_product_id": str(ep.group_product_id),
            "reference_status": ep.reference_status,
            "published_version": ep.published_version,
        }

    @staticmethod
    def _gp_to_dict(gp: GroupProductORM) -> dict:
        return {
            "group_product_id": str(gp.group_product_id),
            "group_product_code": gp.group_product_code,
            "group_product_name": gp.group_product_name,
            "status": gp.status,
        }

    @staticmethod
    def _esku_to_dict(s: EnterpriseSkuORM) -> dict:
        return {
            "enterprise_sku_id": str(s.enterprise_sku_id),
            "enterprise_sku_code": s.enterprise_sku_code,
            "enterprise_sku_name": s.enterprise_sku_name,
            "enterprise_barcode_list": s.enterprise_barcode_list,
            "group_sku_id": str(s.group_sku_id),
            "status": s.status,
        }

    @staticmethod
    def _gsku_to_dict(s: GroupSkuORM) -> dict:
        return {
            "group_sku_id": str(s.group_sku_id),
            "group_sku_code": s.group_sku_code,
            "group_sku_name": s.group_sku_name,
            "barcode_list": s.barcode_list,
            "specification_instance": s.specification_instance,
        }

    @staticmethod
    def _cust_to_dict(c: ProductCustomizationORM) -> dict:
        return {
            "customization_id": str(c.customization_id),
            "sales_price": float(c.sales_price) if c.sales_price is not None else None,
            "purchase_price": float(c.purchase_price) if c.purchase_price is not None else None,
            "inventory_strategy": c.inventory_strategy,
            "safety_stock": float(c.safety_stock) if c.safety_stock is not None else None,
            "cost_model": c.cost_model,
            "custom_attributes": c.custom_attributes,
            "version": c.version,
        }