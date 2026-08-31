"""采购结算路由 - 第二条红线：通过 INV Financial API 落地成本。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.purchasing.pur_app_services import (
    PaymentAppSvc,
    PurchaseSettlementAppSvc,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import (
    CreateSettlementRequest,
    MatchInvoiceRequest,
    ReconcileRequest,
    RequestPaymentRequest,
)

router = APIRouter(prefix="/pur/settlements", tags=["pur-settlement"])


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
@require_permission("pur:settlement:execute")
async def create_settlement(
    req: CreateSettlementRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseSettlementAppSvc(session)
    orm = await svc.create_settlement(
        tenant_id, req.settlement_code, req.order_id, req.supplier_id, req.total_amount,
    )
    await session.commit()
    return {"settlement_id": str(orm.settlement_id), "settlement_code": orm.settlement_code, "status": orm.status}


@router.get("")
@require_permission("pur:settlement:execute")
async def list_settlements(
    order_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    from sqlalchemy import select

    from app.infrastructure.purchasing.models import PurPurchaseSettlementORM
    tenant_id = _get_tenant_id()
    stmt = select(PurPurchaseSettlementORM).where(PurPurchaseSettlementORM.tenant_id == tenant_id)
    if order_id:
        stmt = stmt.where(PurPurchaseSettlementORM.order_id == order_id)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {"settlement_id": str(s.settlement_id), "settlement_code": s.settlement_code,
         "order_id": str(s.order_id), "total_amount": float(s.total_amount),
         "status": s.status}
        for s in rows
    ]


@router.post("/{settlement_id}/reconcile")
@require_permission("pur:settlement:execute")
async def reconcile_settlement(
    settlement_id: UUID,
    req: ReconcileRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseSettlementAppSvc(session)
    orm = await svc.reconcile(tenant_id, settlement_id, req.received_amount)
    await session.commit()
    return {
        "settlement_id": str(orm.settlement_id), "status": orm.status,
        "total_amount": float(orm.total_amount), "received_amount": float(orm.received_amount),
        "diff_amount": float(orm.diff_amount),
    }


@router.post("/{settlement_id}/match-invoice")
@require_permission("pur:settlement:execute")
async def match_invoice(
    settlement_id: UUID,
    req: MatchInvoiceRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseSettlementAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, settlement_id)
    if orm is None:
        return {"error": "not_found"}
    diff = abs(float(orm.total_amount) - req.matched_amount)
    if diff > 0.01:
        orm.status = "diff_found"
    else:
        orm.status = "invoice_matched"
    await session.flush()
    await session.commit()
    return {"settlement_id": str(orm.settlement_id), "status": orm.status, "diff": diff}


@router.post("/{settlement_id}/request-payment")
@require_permission("pur:payment:request")
async def request_payment(
    settlement_id: UUID,
    req: RequestPaymentRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    set_svc = PurchaseSettlementAppSvc(session)
    orm = await set_svc._repo.get_by_id(session, tenant_id, settlement_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "payment_requested"
    await set_svc._session.flush()

    pay_svc = PaymentAppSvc(session)
    pay_orm = await pay_svc.create_payment(
        tenant_id, req.payment_code, settlement_id, orm.supplier_id, req.amount,
    )
    await session.commit()
    return {"settlement_id": str(orm.settlement_id), "payment_id": str(pay_orm.payment_id), "status": orm.status}


@router.get("/{settlement_id}")
@require_permission("pur:settlement:execute")
async def get_settlement(
    settlement_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PurchaseSettlementAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, settlement_id)
    if orm is None:
        return {"error": "not_found"}
    return {
        "settlement_id": str(orm.settlement_id), "settlement_code": orm.settlement_code,
        "order_id": str(orm.order_id), "supplier_id": str(orm.supplier_id),
        "total_amount": float(orm.total_amount), "received_amount": float(orm.received_amount),
        "diff_amount": float(orm.diff_amount), "status": orm.status,
        "inv_transaction_ids": orm.inv_transaction_ids,
    }