"""价格体系管理路由 - /sal/pricing。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import CustomerAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import CustomerPricingRequest

router = APIRouter(prefix="/sal/pricing", tags=["sal-pricing"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.get("")
@require_permission("sal:pricing:manage")
async def list_pricing(
    customer_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    from sqlalchemy import select
    from app.infrastructure.sales.models import SalCustomerPricingORM
    tenant_id = _get_tenant_id()
    stmt = select(SalCustomerPricingORM).where(SalCustomerPricingORM.tenant_id == tenant_id)
    if customer_id:
        stmt = stmt.where(SalCustomerPricingORM.customer_id == customer_id)
    stmt = stmt.offset(offset).limit(limit)
    rows = list((await session.execute(stmt)).scalars().all())
    return [
        {"pricing_id": str(p.pricing_id),
         "customer_id": str(p.customer_id) if p.customer_id else None,
         "category_id": str(p.category_id) if p.category_id else None,
         "enterprise_sku_id": str(p.enterprise_sku_id), "price_type": p.price_type,
         "agreement_price": float(p.agreement_price) if p.agreement_price else None,
         "discount_rate": float(p.discount_rate) if p.discount_rate else None,
         "priority": p.priority, "status": p.status}
        for p in rows
    ]


@router.post("")
@require_permission("sal:pricing:manage")
async def set_pricing(req: CustomerPricingRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.set_pricing(
        tenant_id, req.customer_id, req.enterprise_sku_id, req.price_type,
        req.agreement_price, req.discount_rate, req.priority, req.valid_from, req.valid_until, req.category_id,
    )
    await session.commit()
    return {"pricing_id": str(orm.pricing_id), "price_type": orm.price_type, "status": orm.status}


@router.get("/customer/{customer_id}")
@require_permission("sal:pricing:manage")
async def get_customer_pricing(customer_id: UUID, session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    items = await svc.list_pricing(tenant_id, customer_id)
    return [
        {"pricing_id": str(p.pricing_id), "enterprise_sku_id": str(p.enterprise_sku_id),
         "price_type": p.price_type, "agreement_price": float(p.agreement_price) if p.agreement_price else None,
         "priority": p.priority, "status": p.status}
        for p in items
    ]