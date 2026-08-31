"""企业定制路由 - /api/v1/tenant/mdm/customizations。"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.enterprise_product.enterprise_customization_app_svc import (
    EnterpriseCustomizationAppSvc,
)
from app.domain.inventory.value_objects.shared import CostModelType
from app.domain.enterprise_product.aggregates.product_customization_aggregate import (
    InventoryStrategy,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.mdm import CreateCustomizationRequest, CustomizationResponse

router = APIRouter(prefix="/tenant/mdm/customizations", tags=["mdm-enterprise-customization"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("", response_model=CustomizationResponse, status_code=201)
@require_permission("mdm:enterprise_customization:manage")
async def create_customization(
    req: CreateCustomizationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = EnterpriseCustomizationAppSvc(session)
    inv_strategy = InventoryStrategy(req.inventory_strategy) if req.inventory_strategy else None
    cost_model = CostModelType(req.cost_model) if req.cost_model else None
    agg = await svc.create_customization(
        tenant_id=tenant_id,
        enterprise_product_id=req.enterprise_product_id,
        enterprise_sku_id=req.enterprise_sku_id,
        sales_price=Decimal(str(req.sales_price)) if req.sales_price is not None else None,
        purchase_price=Decimal(str(req.purchase_price)) if req.purchase_price is not None else None,
        inventory_strategy=inv_strategy,
        safety_stock=Decimal(str(req.safety_stock)) if req.safety_stock is not None else None,
        cost_model=cost_model,
        custom_attributes=req.custom_attributes,
    )
    await session.commit()
    return {
        "customization_id": agg.id.value,
        "tenant_id": agg.tenant_id,
        "enterprise_product_id": agg.enterprise_product_id,
        "enterprise_sku_id": agg.enterprise_sku_id,
        "sales_price": float(agg.sales_price) if agg.sales_price else None,
        "purchase_price": float(agg.purchase_price) if agg.purchase_price else None,
        "inventory_strategy": agg.inventory_strategy.value if agg.inventory_strategy else None,
        "safety_stock": float(agg.safety_stock) if agg.safety_stock else None,
        "cost_model": agg.cost_model.value if agg.cost_model else None,
        "custom_attributes": agg.custom_attributes,
        "version": agg.version,
    }


@router.get("/{enterprise_product_id}", response_model=dict)
@require_permission("mdm:enterprise_customization:manage")
async def get_customization(
    enterprise_product_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = EnterpriseCustomizationAppSvc(session)
    orm = await svc.get_customization(tenant_id, enterprise_product_id)
    if orm is None:
        return {}
    return {
        "customization_id": str(orm.customization_id),
        "tenant_id": str(orm.tenant_id),
        "enterprise_product_id": str(orm.enterprise_product_id),
        "enterprise_sku_id": str(orm.enterprise_sku_id) if orm.enterprise_sku_id else None,
        "sales_price": float(orm.sales_price) if orm.sales_price else None,
        "purchase_price": float(orm.purchase_price) if orm.purchase_price else None,
        "inventory_strategy": orm.inventory_strategy,
        "safety_stock": float(orm.safety_stock) if orm.safety_stock else None,
        "cost_model": orm.cost_model,
        "custom_attributes": orm.custom_attributes,
        "version": orm.version,
    }
