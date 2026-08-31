"""商品管理路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inv.inv_app_svc import ProductAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.inv import ProductCreateRequest, ProductResponse

router = APIRouter(prefix="/inv/products", tags=["inv-product"])


@router.post("", response_model=dict, status_code=201)
async def create_product(
    req: ProductCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    svc = ProductAppSvc(session)
    return await svc.create_product(
        tenant_id=tenant_id,
        code=req.product_code,
        name=req.product_name,
        category_id=req.category_id,
        brand_id=req.brand_id,
        base_unit_id=req.base_unit_id,
        description=req.description,
    )


@router.get("", response_model=list[dict])
async def list_products(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    svc = ProductAppSvc(session)
    return await svc.list_products(tenant_id, limit, offset)
