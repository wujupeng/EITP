"""信用额度管理路由 - /sal/credit。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import CustomerAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import CreditLimitRequest

router = APIRouter(prefix="/sal/credit", tags=["sal-credit"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.get("")
@require_permission("sal:credit:manage")
async def list_credit_limits(
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    from sqlalchemy import select
    from app.infrastructure.sales.models import SalCreditLimitORM
    tenant_id = _get_tenant_id()
    rows = list((await session.execute(
        select(SalCreditLimitORM).where(SalCreditLimitORM.tenant_id == tenant_id).offset(offset).limit(limit)
    )).scalars().all())
    return [
        {"credit_limit_id": str(c.credit_limit_id), "customer_id": str(c.customer_id),
         "total_limit": float(c.total_limit), "used_amount": float(c.used_amount),
         "available_amount": float(c.total_limit) - float(c.used_amount),
         "over_credit_strategy": c.over_credit_strategy, "version": c.version}
        for c in rows
    ]


@router.get("/{customer_id}")
@require_permission("sal:credit:manage")
async def get_credit_limit(customer_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.get_credit_limit(tenant_id, customer_id)
    return {
        "credit_limit_id": str(orm.credit_limit_id), "customer_id": str(orm.customer_id),
        "total_limit": float(orm.total_limit), "used_amount": float(orm.used_amount),
        "available_amount": float(orm.total_limit) - float(orm.used_amount),
        "credit_period_days": orm.credit_period_days, "over_credit_strategy": orm.over_credit_strategy,
        "version": orm.version,
    }


@router.post("/{customer_id}")
@require_permission("sal:credit:manage")
async def set_credit_limit(customer_id: UUID, req: CreditLimitRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.set_credit_limit(
        tenant_id, customer_id, req.total_limit, req.credit_period_days, req.over_credit_strategy,
    )
    await session.commit()
    return {"credit_limit_id": str(orm.credit_limit_id), "total_limit": float(orm.total_limit),
            "used_amount": float(orm.used_amount), "version": orm.version}