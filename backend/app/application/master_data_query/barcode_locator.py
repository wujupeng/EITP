"""条码定位 SKU 服务 - 集团条码 + 企业条码两层查询。

集团条码全平台统一，企业条码仅本企业生效。
使用 Redis 缓存（TTL=600s），Redis 故障时降级为数据库查询。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.master_data_query.master_data_query_redis_store import (
    BarcodeLocatorRedisStore,
)
from app.infrastructure.mdm.models import EnterpriseSkuORM, GroupSkuORM
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class BarcodeLocator:
    """条码定位 SKU 服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def locate(self, tenant_id: UUID, barcode: str) -> dict:
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if not ctx.is_authorized("mdm:master_data:query"):
            raise MDMError(MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED, "需要主数据查询权限")

        cached = await BarcodeLocatorRedisStore.get(tenant_id, barcode)
        if cached is not None:
            return cached

        result = await self._locate_enterprise_barcode(tenant_id, barcode)
        if result is None:
            result = await self._locate_group_barcode(tenant_id, barcode)

        if result is not None:
            await BarcodeLocatorRedisStore.set(tenant_id, barcode, result)
        return result or {}

    async def _locate_enterprise_barcode(self, tenant_id: UUID, barcode: str) -> dict | None:
        stmt = select(EnterpriseSkuORM).where(
            EnterpriseSkuORM.tenant_id == tenant_id,
            EnterpriseSkuORM.status == "active",
        )
        skus = list((await self._session.execute(stmt)).scalars().all())
        for sku in skus:
            if sku.enterprise_barcode_list and barcode in sku.enterprise_barcode_list:
                return {
                    "enterprise_sku_id": str(sku.enterprise_sku_id),
                    "enterprise_sku_code": sku.enterprise_sku_code,
                    "enterprise_product_id": str(sku.enterprise_product_id),
                    "barcode_source": "enterprise",
                }
        return None

    async def _locate_group_barcode(self, tenant_id: UUID, barcode: str) -> dict | None:
        stmt = select(EnterpriseSkuORM).where(
            EnterpriseSkuORM.tenant_id == tenant_id,
            EnterpriseSkuORM.status == "active",
        )
        enterprise_skus = list((await self._session.execute(stmt)).scalars().all())
        if not enterprise_skus:
            return None

        group_sku_ids = {sku.group_sku_id for sku in enterprise_skus}
        group_stmt = select(GroupSkuORM).where(
            GroupSkuORM.group_sku_id.in_(group_sku_ids),
            GroupSkuORM.status == "active",
        )
        group_skus = list((await self._session.execute(group_stmt)).scalars().all())
        group_sku_by_id = {s.group_sku_id: s for s in group_skus}

        for sku in enterprise_skus:
            group_sku = group_sku_by_id.get(sku.group_sku_id)
            if group_sku and group_sku.barcode_list and barcode in group_sku.barcode_list:
                return {
                    "enterprise_sku_id": str(sku.enterprise_sku_id),
                    "enterprise_sku_code": sku.enterprise_sku_code,
                    "enterprise_product_id": str(sku.enterprise_product_id),
                    "barcode_source": "group",
                }
        return None

    async def invalidate_cache(self, tenant_id: UUID, barcode: str) -> None:
        await BarcodeLocatorRedisStore.invalidate(tenant_id, barcode)