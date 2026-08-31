"""采购订单路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.purchasing.pur_app_services import PurchaseOrderAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import (
    ApproveRequest,
    ChangeOrderRequest,
    CreatePurchaseOrderRequest,
    PatchPurchaseOrderRequest,
)

router = APIRouter(prefix="/pur/orders", tags=["pur-order"])


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
@require_permission("pur:order:create")
async def create_order(
    req: CreatePurchaseOrderRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    lines = [
        {"sku_id": str(l.sku_id), "ordered_quantity": l.ordered_quantity,
         "unit_price": l.unit_price, "lead_time_days": l.lead_time_days, "remark": l.remark}
        for l in req.lines
    ]
    orm = await svc.create_order(
        tenant_id, req.order_code, req.supplier_id,
        warehouse_id=req.warehouse_id, request_id=req.request_id, lines=lines,
    )
    await session.commit()
    return {"order_id": str(orm.order_id), "order_code": orm.order_code, "status": orm.status}


@router.get("")
@require_permission("pur:order:query")
async def list_orders(
    supplier_id: UUID | None = Query(None),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    items = await svc._repo.list_by_tenant(session, tenant_id, offset, limit)
    result = []
    for o in items:
        if supplier_id and o.supplier_id != supplier_id:
            continue
        if status and o.status != status:
            continue
        result.append({
            "order_id": str(o.order_id), "order_code": o.order_code,
            "supplier_id": str(o.supplier_id), "total_amount": float(o.total_amount),
            "status": o.status,
        })
    return result


@router.get("/{order_id}")
@require_permission("pur:order:query")
async def get_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, order_id)
    if orm is None:
        return {"error": "not_found"}
    lines = await svc._repo.list_lines(session, tenant_id, order_id)
    return {
        "order_id": str(orm.order_id), "order_code": orm.order_code,
        "supplier_id": str(orm.supplier_id), "warehouse_id": str(orm.warehouse_id) if orm.warehouse_id else None,
        "total_amount": float(orm.total_amount), "status": orm.status,
        "approved_by": str(orm.approved_by) if orm.approved_by else None,
        "lines": [
            {"line_id": str(l.line_id), "sku_id": str(l.sku_id),
             "ordered_quantity": float(l.ordered_quantity), "received_quantity": float(l.received_quantity),
             "unit_price": float(l.unit_price)}
            for l in lines
        ],
    }


@router.patch("/{order_id}")
@require_permission("pur:order:create")
async def patch_order(
    order_id: UUID,
    req: PatchPurchaseOrderRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, order_id)
    if orm is None:
        return {"error": "not_found"}
    if req.warehouse_id:
        orm.warehouse_id = req.warehouse_id
    await session.flush()
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.post("/{order_id}/submit")
@require_permission("pur:order:create")
async def submit_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, order_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "submitted"
    await session.flush()
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.post("/{order_id}/approve")
@require_permission("pur:order:approve")
async def approve_order(
    order_id: UUID,
    req: ApproveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = PurchaseOrderAppSvc(session)
    if not req.approved:
        orm = await svc._repo.get_by_id(session, tenant_id, order_id)
        if orm:
            orm.status = "rejected"
            await session.flush()
            await session.commit()
            return {"order_id": str(orm.order_id), "status": orm.status}
        return {"error": "not_found"}
    orm = await svc.approve_order(tenant_id, order_id, user_id)
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.post("/{order_id}/send")
@require_permission("pur:order:send")
async def send_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    orm = await svc.send_order(tenant_id, order_id)
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.post("/{order_id}/change")
@require_permission("pur:order:change")
async def change_order(
    order_id: UUID,
    req: ChangeOrderRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, order_id)
    if orm is None:
        return {"error": "not_found"}
    if req.lines:
        from app.infrastructure.purchasing.models import PurPurchaseOrderLineORM
        old_lines = await svc._repo.list_lines(session, tenant_id, order_id)
        for ol in old_lines:
            await session.delete(ol)
        for l in req.lines:
            session.add(PurPurchaseOrderLineORM(
                tenant_id=tenant_id, order_id=order_id,
                sku_id=l.sku_id, ordered_quantity=l.ordered_quantity,
                unit_price=l.unit_price, lead_time_days=l.lead_time_days, remark=l.remark,
            ))
        orm.total_amount = sum(l.ordered_quantity * l.unit_price for l in req.lines)
    await session.flush()
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status, "total_amount": float(orm.total_amount)}


@router.post("/{order_id}/cancel")
@require_permission("pur:order:cancel")
async def cancel_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    orm = await svc.cancel_order(tenant_id, order_id)
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.post("/{order_id}/close")
@require_permission("pur:order:close")
async def close_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, order_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "closed"
    await session.flush()
    await session.commit()
    return {"order_id": str(orm.order_id), "status": orm.status}


@router.get("/{order_id}/trace")
@require_permission("pur:order:query")
async def trace_order(
    order_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseOrderAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, order_id)
    if orm is None:
        return {"error": "not_found"}
    lines = await svc._repo.list_lines(session, tenant_id, order_id)
    return {
        "order_id": str(orm.order_id), "order_code": orm.order_code, "status": orm.status,
        "total_ordered": sum(float(l.ordered_quantity) for l in lines),
        "total_received": sum(float(l.received_quantity) for l in lines),
        "lines": [
            {"sku_id": str(l.sku_id), "ordered": float(l.ordered_quantity), "received": float(l.received_quantity)}
            for l in lines
        ],
    }