"""销售订单路由 - design 2.3.2.3。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import SalesOrderAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import (
    ApproveRequest, ChangeOrderRequest, CreateSalesOrderRequest,
    UpdateSalesOrderRequest,
)

router = APIRouter(prefix="/sal/orders", tags=["sal-order"])


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
@require_permission("sal:order:create")
async def create_order(req: CreateSalesOrderRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    lines = [
        {"enterprise_sku_id": str(l.enterprise_sku_id), "ordered_quantity": l.ordered_quantity,
         "unit_price": l.unit_price, "expected_delivery_date": l.expected_delivery_date}
        for l in req.lines
    ]
    orm = await svc.create_order(
        tenant_id, req.order_code, req.customer_id, lines, req.idempotency_key,
        shipping_warehouse_id=req.shipping_warehouse_id, source_quotation_id=req.source_quotation_id,
        payment_terms=req.payment_terms, currency=req.currency,
    )
    await session.commit()
    return {"order_id": str(orm.order_id), "order_code": orm.order_code,
            "status": orm.status, "total_amount": float(orm.total_amount)}


@router.get("")
@require_permission("sal:order:query")
async def list_orders(
    status: str | None = Query(None), customer_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    items = await svc.list_orders(tenant_id, status, customer_id, offset, limit)
    return [
        {"order_id": str(o.order_id), "order_code": o.order_code,
         "customer_id": str(o.customer_id), "total_amount": float(o.total_amount),
         "status": o.status, "version": o.version}
        for o in items
    ]


@router.get("/{order_id}")
@require_permission("sal:order:query")
async def get_order(order_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    orm = await svc.get_order(tenant_id, order_id)
    lines = await svc._repo.list_lines(session, tenant_id, order_id)
    return {
        "order_id": str(orm.order_id), "order_code": orm.order_code,
        "customer_id": str(orm.customer_id),
        "shipping_warehouse_id": str(orm.shipping_warehouse_id) if orm.shipping_warehouse_id else None,
        "source_quotation_id": str(orm.source_quotation_id) if orm.source_quotation_id else None,
        "total_amount": float(orm.total_amount), "status": orm.status, "version": orm.version,
        "reservation_ids": orm.reservation_ids,
        "lines": [
            {"line_id": str(l.line_id), "enterprise_sku_id": str(l.enterprise_sku_id),
             "ordered_quantity": float(l.ordered_quantity), "reserved_quantity": float(l.reserved_quantity),
             "shipped_quantity": float(l.shipped_quantity),
             "remaining_quantity": float(l.ordered_quantity) - float(l.shipped_quantity),
             "unit_price": float(l.unit_price), "status": l.status}
            for l in lines
        ],
    }


@router.patch("/{order_id}")
@require_permission("sal:order:create")
async def patch_order(order_id: UUID, req: UpdateSalesOrderRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    orm = await svc.update_order(tenant_id, order_id, **req.model_dump(exclude_none=True))
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.post("/{order_id}/submit")
@require_permission("sal:order:create")
async def submit_order(order_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    orm = await svc.submit_order(tenant_id, order_id)
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.post("/{order_id}/approve")
@require_permission("sal:order:approve")
async def approve_order(order_id: UUID, req: ApproveRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = SalesOrderAppSvc(session)
    orm = await svc.approve_order(tenant_id, order_id, req.approved, user_id)
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.post("/{order_id}/confirm")
@require_permission("sal:order:confirm")
async def confirm_order(order_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    orm = await svc.confirm_order(tenant_id, order_id)
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status, "reservation_ids": orm.reservation_ids}


@router.post("/{order_id}/change")
@require_permission("sal:order:change")
async def change_order(order_id: UUID, req: ChangeOrderRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    lines = [
        {"enterprise_sku_id": str(l.enterprise_sku_id), "ordered_quantity": l.ordered_quantity,
         "unit_price": l.unit_price, "expected_delivery_date": l.expected_delivery_date}
        for l in req.lines
    ]
    orm = await svc.change_order(tenant_id, order_id, lines, req.reason)
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status, "version": orm.version}


@router.post("/{order_id}/cancel")
@require_permission("sal:order:cancel")
async def cancel_order(order_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    orm = await svc.cancel_order(tenant_id, order_id)
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.post("/{order_id}/close")
@require_permission("sal:order:close")
async def close_order(order_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    orm = await svc.close_order(tenant_id, order_id)
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.get("/{order_id}/trace")
@require_permission("sal:order:query")
async def trace_order(order_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesOrderAppSvc(session)
    orm = await svc.get_order(tenant_id, order_id)
    lines = await svc._repo.list_lines(session, tenant_id, order_id)
    audits = await svc._audit_repo.query_by_order(session, tenant_id, order_id)
    return {
        "order_id": str(orm.order_id), "order_code": orm.order_code, "status": orm.status,
        "total_ordered": sum(float(l.ordered_quantity) for l in lines),
        "total_shipped": sum(float(l.shipped_quantity) for l in lines),
        "reservation_ids": orm.reservation_ids,
        "audit_chain": [
            {"audit_id": str(a.audit_id), "event_type": a.event_type,
             "operated_at": str(a.operated_at) if a.operated_at else None}
            for a in audits
        ],
    }