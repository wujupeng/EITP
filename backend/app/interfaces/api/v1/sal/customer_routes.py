"""客户管理路由 - design 2.3.2.1。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import CustomerAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import (
    ApproveRequest, CreateCustomerRequest, CreditLimitRequest,
    CustomerPricingRequest, UpdateCustomerRequest,
)

router = APIRouter(prefix="/sal/customers", tags=["sal-customer"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("")
@require_permission("sal:customer:manage")
async def create_customer(req: CreateCustomerRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.create_customer(
        tenant_id, req.customer_code, req.customer_name, req.customer_type,
        tax_id=req.tax_id, contact_info=req.contact_info.model_dump(),
        bank_account=req.bank_account.model_dump(),
    )
    await session.commit()
    return {"customer_id": str(orm.customer_id), "customer_code": orm.customer_code, "status": orm.status}


@router.get("")
@require_permission("sal:customer:query")
async def list_customers(
    status: str | None = Query(None), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    items = await svc.list_customers(tenant_id, status, offset, limit)
    return [
        {"customer_id": str(c.customer_id), "customer_code": c.customer_code,
         "customer_name": c.customer_name, "customer_type": c.customer_type,
         "status": c.status, "published_version": c.published_version}
        for c in items
    ]


@router.get("/{customer_id}")
@require_permission("sal:customer:query")
async def get_customer(customer_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.get_customer(tenant_id, customer_id)
    return {
        "customer_id": str(orm.customer_id), "customer_code": orm.customer_code,
        "customer_name": orm.customer_name, "customer_type": orm.customer_type,
        "tax_id": orm.tax_id, "status": orm.status,
        "published_version": orm.published_version, "governance_state": orm.governance_state,
    }


@router.patch("/{customer_id}")
@require_permission("sal:customer:manage")
async def patch_customer(customer_id: UUID, req: UpdateCustomerRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    kwargs = req.model_dump(exclude_none=True)
    if kwargs.get("contact_info"):
        kwargs["contact_info"] = req.contact_info.model_dump()
    if kwargs.get("bank_account"):
        kwargs["bank_account"] = req.bank_account.model_dump()
    orm = await svc.update_customer(tenant_id, customer_id, **kwargs)
    await session.commit()
    return {"customer_id": str(orm.customer_id), "status": orm.status}


@router.post("/{customer_id}/submit")
@require_permission("sal:customer:manage")
async def submit_customer(customer_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.submit_customer(tenant_id, customer_id)
    await session.commit()
    return {"customer_id": str(orm.customer_id), "status": orm.status}


@router.post("/{customer_id}/approve")
@require_permission("sal:customer:manage")
async def approve_customer(customer_id: UUID, req: ApproveRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = CustomerAppSvc(session)
    orm = await svc.approve_customer(tenant_id, customer_id, req.approved, user_id)
    await session.commit()
    return {"customer_id": str(orm.customer_id), "status": orm.status}


@router.post("/{customer_id}/publish")
@require_permission("sal:customer:manage")
async def publish_customer(customer_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.publish_customer(tenant_id, customer_id)
    await session.commit()
    return {"customer_id": str(orm.customer_id), "status": orm.status, "published_version": orm.published_version}


@router.post("/{customer_id}/disable")
@require_permission("sal:customer:manage")
async def disable_customer(customer_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.disable_customer(tenant_id, customer_id)
    await session.commit()
    return {"customer_id": str(orm.customer_id), "status": orm.status}


@router.post("/{customer_id}/credit-limit")
@require_permission("sal:credit:manage")
async def set_credit_limit(customer_id: UUID, req: CreditLimitRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.set_credit_limit(
        tenant_id, customer_id, req.total_limit, req.credit_period_days, req.over_credit_strategy,
    )
    await session.commit()
    return {"credit_limit_id": str(orm.credit_limit_id), "total_limit": float(orm.total_limit), "used_amount": float(orm.used_amount)}


@router.get("/{customer_id}/credit-limit")
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


@router.post("/{customer_id}/pricing")
@require_permission("sal:pricing:manage")
async def set_pricing(customer_id: UUID, req: CustomerPricingRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    orm = await svc.set_pricing(
        tenant_id, req.customer_id or customer_id, req.enterprise_sku_id, req.price_type,
        req.agreement_price, req.discount_rate, req.priority, req.valid_from, req.valid_until, req.category_id,
    )
    await session.commit()
    return {"pricing_id": str(orm.pricing_id), "price_type": orm.price_type, "status": orm.status}


@router.get("/{customer_id}/pricing")
@require_permission("sal:pricing:manage")
async def get_pricing(customer_id: UUID, session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = CustomerAppSvc(session)
    items = await svc.list_pricing(tenant_id, customer_id)
    return [
        {"pricing_id": str(p.pricing_id), "enterprise_sku_id": str(p.enterprise_sku_id),
         "price_type": p.price_type, "agreement_price": float(p.agreement_price) if p.agreement_price else None,
         "priority": p.priority, "status": p.status}
        for p in items
    ]