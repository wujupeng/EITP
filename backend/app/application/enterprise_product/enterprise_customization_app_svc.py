"""企业定制应用服务 - 企业级差异化定制 CRUD，经企业级治理工作流审批发布后生效。"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enterprise_product.aggregates.product_customization_aggregate import (
    CostModelType,
    InventoryStrategy,
    ProductCustomizationAggregate,
)
from app.domain.shared.entity import EntityId
from app.infrastructure.enterprise_product.enterprise_product_repository import (
    ProductCustomizationRepository,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class EnterpriseCustomizationAppSvc:
    """企业定制应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProductCustomizationRepository()

    async def create_customization(
        self,
        tenant_id: UUID,
        enterprise_product_id: UUID,
        enterprise_sku_id: UUID | None = None,
        sales_price: Decimal | None = None,
        purchase_price: Decimal | None = None,
        inventory_strategy: InventoryStrategy | None = None,
        safety_stock: Decimal | None = None,
        cost_model: CostModelType | None = None,
        custom_attributes: dict | None = None,
    ) -> ProductCustomizationAggregate:
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(MDMErrorCode.DIRECT_ACCESS_DENIED, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise MDMError(MDMErrorCode.CROSS_TENANT_POLICY_DENIED, "跨租户操作被拒绝")

        agg = ProductCustomizationAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            enterprise_product_id=enterprise_product_id,
            enterprise_sku_id=enterprise_sku_id,
            sales_price=sales_price,
            purchase_price=purchase_price,
            inventory_strategy=inventory_strategy,
            safety_stock=safety_stock,
            cost_model=cost_model,
            custom_attributes=custom_attributes,
        )
        await self._repo.save(self._session, agg)
        return agg

    async def get_customization(self, tenant_id: UUID, enterprise_product_id: UUID):
        return await self._repo.get_by_product(self._session, tenant_id, enterprise_product_id)