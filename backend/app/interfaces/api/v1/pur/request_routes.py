"""采购申请路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.purchasing.pur_app_services import PurchaseRequestAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import ApproveRequest, CreatePurchaseRequestRequest

router = APIRouter(prefix="/pur/requests", tags=["pur-request"])


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
@require_permission("pur:request:create")
async def create_request(
    req: CreatePurchaseRequestRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseRequestAppSvc(session)
    lines = [
        {"sku_id": str(l.sku_id), "quantity": l.quantity, "unit_price": l.unit_price, "remark": l.remark}
        for l in req.lines
    ]
    orm = await svc.create_request(
        tenant_id, req.request_code, req.title,
        department_id=req.department_id, budget_id=req.budget_id, lines=lines,
    )
    await session.commit()
    return {"request_id": str(orm.request_id), "request_code": orm.request_code, "status": orm.status}


@router.get("")
@require_permission("pur:request:query")
async def list_requests(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = PurchaseRequestAppSvc(session)
    items = await svc._repo.list_by_tenant(session, tenant_id, offset, limit)
    return [
        {"request_id": str(r.request_id), "request_code": r.request_code,
         "title": r.title, "total_amount": float(r.total_amount), "status": r.status}
        for r in items
    ]


@router.get("/{request_id}")
@require_permission("pur:request:query")
async def get_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseRequestAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, request_id)
    if orm is None:
        return {"error": "not_found"}
    lines = await svc._repo.list_lines(session, tenant_id, request_id)
    return {
        "request_id": str(orm.request_id), "request_code": orm.request_code,
        "title": orm.title, "total_amount": float(orm.total_amount), "status": orm.status,
        "lines": [
            {"line_id": str(l.line_id), "sku_id": str(l.sku_id),
             "quantity": float(l.quantity), "unit_price": float(l.unit_price) if l.unit_price else None}
            for l in lines
        ],
    }


@router.post("/{request_id}/submit")
@require_permission("pur:request:create")
async def submit_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseRequestAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, request_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "submitted"
    await session.flush()
    await session.commit()
    return {"request_id": str(orm.request_id), "status": orm.status}


@router.post("/{request_id}/approve")
@require_permission("pur:request:approve")
async def approve_request(
    request_id: UUID,
    req: ApproveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = PurchaseRequestAppSvc(session)
    if not req.approved:
        orm = await svc._repo.get_by_id(session, tenant_id, request_id)
        if orm:
            orm.status = "rejected"
            await session.flush()
            await session.commit()
            return {"request_id": str(orm.request_id), "status": orm.status}
        return {"error": "not_found"}
    orm = await svc.approve_request(tenant_id, request_id, user_id)
    await session.commit()
    return {"request_id": str(orm.request_id), "status": orm.status}


@router.post("/{request_id}/convert")
@require_permission("pur:request:create")
async def convert_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()

    svc = PurchaseRequestAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, request_id)
    if orm is None:
        return {"error": "not_found"}
    if orm.status != "approved":
        return {"error": "not_approved"}
    from app.application.purchasing.pur_app_services import PurchaseOrderAppSvc
    order_svc = PurchaseOrderAppSvc(session)
    lines = await svc._repo.list_lines(session, tenant_id, request_id)
    order_code = f"PO-{orm.request_code}"
    order_orm = await order_svc.create_order(
        tenant_id, order_code, orm.supplier_id if hasattr(orm, 'supplier_id') else None,
        lines=[{"sku_id": str(l.sku_id), "ordered_quantity": float(l.quantity),
                "unit_price": float(l.unit_price) if l.unit_price else 0}
               for l in lines],
    )
    orm.converted_order_id = order_orm.order_id
    orm.status = "converted"
    await session.flush()
    await session.commit()
    return {"request_id": str(orm.request_id), "order_id": str(order_orm.order_id), "status": orm.status}


@router.post("/{request_id}/cancel")
@require_permission("pur:request:create")
async def cancel_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseRequestAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, request_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "cancelled"
    await session.flush()
    await session.commit()
    return {"request_id": str(orm.request_id), "status": orm.status}