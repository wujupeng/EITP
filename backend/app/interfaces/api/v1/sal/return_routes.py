"""销售退货路由 - design 2.3.2.5，红线一：通过 WMS Receiving API。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import SalesReturnAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import (
    ApproveRequest, CreateSalesReturnRequest, DispositionRequest,
    QcResultRequest, ReturnReceiveRequest,
)

router = APIRouter(prefix="/sal/returns", tags=["sal-return"])


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
@require_permission("sal:return:create")
async def create_return(req: CreateSalesReturnRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesReturnAppSvc(session)
    lines = [
        {"order_line_id": str(l.order_line_id), "enterprise_sku_id": str(l.enterprise_sku_id),
         "return_quantity": l.return_quantity, "refund_amount": l.refund_amount,
         "shipment_line_id": str(l.shipment_line_id) if l.shipment_line_id else None}
        for l in req.lines
    ]
    orm = await svc.create_return(
        tenant_id, req.return_code, req.order_id, req.original_shipment_id, lines,
        req.return_reason, req.idempotency_key,
    )
    await session.commit()
    return {"return_id": str(orm.return_id), "return_code": orm.return_code, "status": orm.status}


@router.get("")
@require_permission("sal:return:create")
async def list_returns(
    status: str | None = Query(None), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = SalesReturnAppSvc(session)
    items = await svc.list_returns(tenant_id, status, offset, limit)
    return [
        {"return_id": str(r.return_id), "return_code": r.return_code,
         "order_id": str(r.order_id), "status": r.status}
        for r in items
    ]


@router.post("/{return_id}/submit")
@require_permission("sal:return:create")
async def submit_return(return_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesReturnAppSvc(session)
    orm = await svc.submit_return(tenant_id, return_id)
    await session.commit()
    return {"return_id": str(orm.return_id), "status": orm.status}


@router.post("/{return_id}/approve")
@require_permission("sal:return:approve")
async def approve_return(return_id: UUID, req: ApproveRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = SalesReturnAppSvc(session)
    orm = await svc.approve_return(tenant_id, return_id, req.approved, user_id)
    await session.commit()
    return {"return_id": str(orm.return_id), "status": orm.status}


@router.post("/{return_id}/receive")
@require_permission("sal:return:execute")
async def receive_return(return_id: UUID, req: ReturnReceiveRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesReturnAppSvc(session)
    orm = await svc.execute_return(tenant_id, return_id, req.idempotency_key)
    await session.commit()
    return {"return_id": str(orm.return_id), "status": orm.status,
            "wms_receiving_id": str(orm.wms_receiving_id) if orm.wms_receiving_id else None,
            "inv_transaction_ids": orm.inv_transaction_ids}


@router.post("/{return_id}/qc")
@require_permission("sal:return:execute")
async def qc_return(return_id: UUID, req: QcResultRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesReturnAppSvc(session)
    line = await svc.qc_return(tenant_id, return_id, req.line_id, req.qc_result, req.qc_note)
    await session.commit()
    return {"line_id": str(line.line_id), "qc_result": line.qc_result}


@router.post("/{return_id}/dispose")
@require_permission("sal:return:execute")
async def dispose_return(return_id: UUID, req: DispositionRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesReturnAppSvc(session)
    orm = await svc.dispose_return(tenant_id, return_id, req.line_id, req.disposition)
    await session.commit()
    return {"return_id": str(orm.return_id), "status": orm.status, "refund_amount": float(orm.refund_amount)}


@router.get("/{return_id}")
@require_permission("sal:return:create")
async def get_return(return_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesReturnAppSvc(session)
    orm = await svc.get_return(tenant_id, return_id)
    lines = await svc._repo.list_lines(session, tenant_id, return_id)
    return {
        "return_id": str(orm.return_id), "return_code": orm.return_code,
        "order_id": str(orm.order_id), "original_shipment_id": str(orm.original_shipment_id),
        "status": orm.status, "refund_amount": float(orm.refund_amount),
        "wms_receiving_id": str(orm.wms_receiving_id) if orm.wms_receiving_id else None,
        "inv_transaction_ids": orm.inv_transaction_ids,
        "lines": [
            {"line_id": str(l.line_id), "enterprise_sku_id": str(l.enterprise_sku_id),
             "return_quantity": float(l.return_quantity), "qc_result": l.qc_result, "disposition": l.disposition}
            for l in lines
        ],
    }