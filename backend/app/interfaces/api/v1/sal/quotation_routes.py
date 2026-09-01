"""销售报价路由 - design 2.3.2.2。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import SalesQuotationAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import (
    ApproveRequest, ConvertRequest, CreateSalesQuotationRequest,
)

router = APIRouter(prefix="/sal/quotations", tags=["sal-quotation"])


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
@require_permission("sal:quotation:create")
async def create_quotation(req: CreateSalesQuotationRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesQuotationAppSvc(session)
    lines = [
        {"enterprise_sku_id": str(l.enterprise_sku_id), "quantity": l.quantity,
         "unit_price": l.unit_price, "expected_delivery_date": l.expected_delivery_date}
        for l in req.lines
    ]
    orm = await svc.create_quotation(
        tenant_id, req.quotation_code, req.customer_id, lines,
        valid_from=req.valid_from, valid_until=req.valid_until,
        payment_terms=req.payment_terms, currency=req.currency,
    )
    await session.commit()
    return {"quotation_id": str(orm.quotation_id), "quotation_code": orm.quotation_code, "status": orm.status}


@router.get("")
@require_permission("sal:quotation:create")
async def list_quotations(
    status: str | None = Query(None), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = SalesQuotationAppSvc(session)
    items = await svc.list_quotations(tenant_id, status, offset, limit)
    return [
        {"quotation_id": str(q.quotation_id), "quotation_code": q.quotation_code,
         "customer_id": str(q.customer_id), "status": q.status}
        for q in items
    ]


@router.get("/{quotation_id}")
@require_permission("sal:quotation:create")
async def get_quotation(quotation_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesQuotationAppSvc(session)
    orm = await svc.get_quotation(tenant_id, quotation_id)
    lines = await svc._repo.list_lines(session, tenant_id, quotation_id)
    return {
        "quotation_id": str(orm.quotation_id), "quotation_code": orm.quotation_code,
        "customer_id": str(orm.customer_id), "status": orm.status,
        "governance_state": orm.governance_state,
        "valid_from": str(orm.valid_from) if orm.valid_from else None,
        "valid_until": str(orm.valid_until) if orm.valid_until else None,
        "converted_order_id": str(orm.converted_order_id) if orm.converted_order_id else None,
        "lines": [
            {"line_id": str(l.line_id), "enterprise_sku_id": str(l.enterprise_sku_id),
             "quantity": float(l.quantity), "unit_price": float(l.unit_price)}
            for l in lines
        ],
    }


@router.post("/{quotation_id}/submit")
@require_permission("sal:quotation:create")
async def submit_quotation(quotation_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesQuotationAppSvc(session)
    orm = await svc.submit_quotation(tenant_id, quotation_id)
    await session.commit()
    return {"quotation_id": str(orm.quotation_id), "status": orm.status}


@router.post("/{quotation_id}/approve")
@require_permission("sal:quotation:approve")
async def approve_quotation(quotation_id: UUID, req: ApproveRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = SalesQuotationAppSvc(session)
    orm = await svc.approve_quotation(tenant_id, quotation_id, req.approved, user_id)
    await session.commit()
    return {"quotation_id": str(orm.quotation_id), "status": orm.status}


@router.post("/{quotation_id}/convert")
@require_permission("sal:quotation:convert")
async def convert_quotation(quotation_id: UUID, req: ConvertRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesQuotationAppSvc(session)
    order = await svc.convert_to_order(tenant_id, quotation_id, req.order_code)
    await session.commit()
    return {"quotation_id": str(quotation_id), "order_id": str(order.order_id),
            "order_code": order.order_code, "status": order.status}


@router.post("/{quotation_id}/cancel")
@require_permission("sal:quotation:create")
async def cancel_quotation(quotation_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesQuotationAppSvc(session)
    orm = await svc.cancel_quotation(tenant_id, quotation_id)
    await session.commit()
    return {"quotation_id": str(orm.quotation_id), "status": orm.status}