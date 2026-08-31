"""商品引用关系应用服务 - 引用关系查询（集团管理员视角/企业管理员视角）。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.enterprise_product.enterprise_product_repository import (
    ProductReferenceRepository,
)


class ProductReferenceAppSvc:
    """商品引用关系应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProductReferenceRepository()

    async def list_references_by_group_product(self, group_product_id: UUID):
        """集团管理员视角：查询某集团商品被哪些企业引用。"""
        return await self._repo.list_by_group_product(self._session, group_product_id)

    async def list_references_by_tenant(self, tenant_id: UUID):
        """企业管理员视角：查询本企业引用了哪些集团商品。"""
        return await self._repo.list_by_tenant(self._session, tenant_id)