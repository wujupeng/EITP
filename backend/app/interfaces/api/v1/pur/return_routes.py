"""采购退货路由 - 第一条红线：退货出库通过 INV RETURN_OUT 或 WMS Shipping API 落地。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.purchasing.pur_app_services import PurchaseReturnAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import (
    ApproveRequest,
    CreatePurchaseReturnRequest,
    ReturnShipRequest,
)

router = APIRouter(prefix="/pur/returns", tags=["pur-return"])


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
@require_permission("pur:return:create")
async def create_return(
    req: CreatePurchaseReturnRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseReturnAppSvc(session)
    lines = [
        {"order_line_id": str(l.order_line_id), "sku_id": str(l.sku_id),
         "return_quantity": l.return_quantity, "reason": l.reason}
        for l in req.lines
    ]
    orm = await svc.create_return(
        tenant_id, req.return_code, req.order_id, req.supplier_id,
        warehouse_id=req.warehouse_id, lines=lines,
    )
    await session.commit()
    return {"return_id": str(orm.return_id), "return_code": orm.return_code, "status": orm.status}


@router.get("")
@require_permission("pur:return:query")
async def list_returns(
    order_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    from sqlalchemy import select

    from app.infrastructure.purchasing.models import PurPurchaseReturnORM
    tenant_id = _get_tenant_id()
    stmt = select(PurPurchaseReturnORM).where(PurPurchaseReturnORM.tenant_id == tenant_id)
    if order_id:
        stmt = stmt.where(PurPurchaseReturnORM.order_id == order_id)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {"return_id": str(r.return_id), "return_code": r.return_code,
         "order_id": str(r.order_id), "status": r.status}
        for r in rows
    ]


@router.post("/{return_id}/submit")
@require_permission("pur:return:create")
async def submit_return(
    return_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseReturnAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, return_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "submitted"
    await session.flush()
    await session.commit()
    return {"return_id": str(orm.return_id), "status": orm.status}


@router.post("/{return_id}/approve")
@require_permission("pur:return:approve")
async def approve_return(
    return_id: UUID,
    req: ApproveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = PurchaseReturnAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, return_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "approved" if req.approved else "rejected"
    orm.approved_by = user_id if req.approved else None
    await session.flush()
    await session.commit()
    return {"return_id": str(orm.return_id), "status": orm.status}


@router.post("/{return_id}/ship")
@require_permission("pur:return:create")
async def ship_return(
    return_id: UUID,
    req: ReturnShipRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()

    svc = PurchaseReturnAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, return_id)
    if orm is None:
        return {"error": "not_found"}
    if orm.status != "approved":
        return {"error": "not_approved"}

    from datetime import datetime, timezone

    import httpx
    inv_tx_ids: list[str] = []
    lines = await svc._repo.list_lines(session, tenant_id, return_id)

    if req.via_wms_shipping and orm.warehouse_id:
        async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1/wms", timeout=30) as client:
            for line in lines:
                resp = await client.post("/shipping/orders", json={
                    "tenant_id": str(tenant_id), "document_id": str(return_id),
                    "document_type": "purchase_return", "sku_id": str(line.sku_id),
                    "quantity": float(line.return_quantity),
                    "warehouse_id": str(orm.warehouse_id),
                })
                if resp.status_code in (200, 201):
                    inv_tx_ids.extend(resp.json().get("inv_transaction_ids", []))
    else:
        async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1/inv", timeout=30) as client:
            for line in lines:
                resp = await client.post("/inventory/transactions", json={
                    "transaction_type": "RETURN_OUT", "tenant_id": str(tenant_id),
                    "sku_id": str(line.sku_id), "warehouse_id": str(orm.warehouse_id),
                    "quantity": float(line.return_quantity), "document_id": str(return_id),
                })
                if resp.status_code in (200, 201):
                    data = resp.json()
                    inv_tx_ids.append(data.get("transaction_id", ""))

    orm.status = "shipped"
    orm.inv_transaction_ids = inv_tx_ids
    orm.shipped_at = datetime.now(timezone.utc)
    await session.flush()
    await session.commit()
    return {"return_id": str(orm.return_id), "status": orm.status, "inv_transaction_ids": inv_tx_ids}


@router.get("/{return_id}")
@require_permission("pur:return:query")
async def get_return(
    return_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseReturnAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, return_id)
    if orm is None:
        return {"error": "not_found"}
    lines = await svc._repo.list_lines(session, tenant_id, return_id)
    return {
        "return_id": str(orm.return_id), "return_code": orm.return_code,
        "order_id": str(orm.order_id), "status": orm.status,
        "inv_transaction_ids": orm.inv_transaction_ids,
        "lines": [
            {"line_id": str(l.line_id), "sku_id": str(l.sku_id),
             "return_quantity": float(l.return_quantity), "reason": l.reason}
            for l in lines
        ],
    }