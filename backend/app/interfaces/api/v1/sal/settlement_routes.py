"""销售结算路由 - design 2.3.2.6，红线二：通过 INV Financial/Revenue API。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import SalesSettlementAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import (
    CreateSettlementRequest, LandRevenueRequest, MatchInvoiceRequest,
    ReconcileRequest, RequestPaymentRequest,
)

router = APIRouter(prefix="/sal/settlements", tags=["sal-settlement"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("")
@require_permission("sal:settlement:execute")
async def create_settlement(req: CreateSettlementRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesSettlementAppSvc(session)
    orm = await svc.create_settlement(
        tenant_id, req.settlement_code, req.order_id, req.receivable_amount, req.idempotency_key,
    )
    await session.commit()
    return {"settlement_id": str(orm.settlement_id), "settlement_code": orm.settlement_code, "status": orm.status}


@router.get("")
@require_permission("sal:settlement:execute")
async def list_settlements(
    status: str | None = Query(None), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = SalesSettlementAppSvc(session)
    items = await svc.list_settlements(tenant_id, status, offset, limit)
    return [
        {"settlement_id": str(s.settlement_id), "settlement_code": s.settlement_code,
         "order_id": str(s.order_id), "net_receivable_amount": float(s.net_receivable_amount),
         "status": s.status, "revenue_landed": s.revenue_landed}
        for s in items
    ]


@router.post("/{settlement_id}/reconcile")
@require_permission("sal:settlement:execute")
async def reconcile_settlement(settlement_id: UUID, req: ReconcileRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesSettlementAppSvc(session)
    orm = await svc.reconcile(tenant_id, settlement_id, req.received_amount, req.diff_threshold)
    await session.commit()
    return {"settlement_id": str(orm.settlement_id), "status": orm.status,
            "net_receivable_amount": float(orm.net_receivable_amount)}


@router.post("/{settlement_id}/match-invoice")
@require_permission("sal:settlement:execute")
async def match_invoice(settlement_id: UUID, req: MatchInvoiceRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesSettlementAppSvc(session)
    orm = await svc.match_invoice(tenant_id, settlement_id, req.invoice_id, req.matched_amount, req.diff_threshold)
    await session.commit()
    return {"settlement_id": str(orm.settlement_id), "status": orm.status, "invoice_id": str(orm.invoice_id)}


@router.post("/{settlement_id}/request-payment")
@require_permission("sal:payment:request")
async def request_payment(settlement_id: UUID, req: RequestPaymentRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesSettlementAppSvc(session)
    pay_orm = await svc.request_payment(tenant_id, settlement_id, req.payment_code, req.amount)
    await session.commit()
    return {"settlement_id": str(settlement_id), "payment_receipt_id": str(pay_orm.payment_receipt_id),
            "status": "payment_requested"}


@router.post("/{settlement_id}/land-revenue")
@require_permission("sal:settlement:execute")
async def land_revenue(settlement_id: UUID, req: LandRevenueRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesSettlementAppSvc(session)
    result = await svc.land_revenue(
        tenant_id, settlement_id, req.sku_id, req.warehouse_id, req.quantity,
        req.unit_price, req.moving_avg_cost, req.idempotency_key,
    )
    await session.commit()
    return result


@router.get("/{settlement_id}")
@require_permission("sal:settlement:execute")
async def get_settlement(settlement_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesSettlementAppSvc(session)
    orm = await svc.get_settlement(tenant_id, settlement_id)
    return {
        "settlement_id": str(orm.settlement_id), "settlement_code": orm.settlement_code,
        "order_id": str(orm.order_id), "receivable_amount": float(orm.receivable_amount),
        "refund_amount": float(orm.refund_amount), "net_receivable_amount": float(orm.net_receivable_amount),
        "status": orm.status, "revenue_landed": orm.revenue_landed,
        "invoice_id": str(orm.invoice_id) if orm.invoice_id else None,
        "payment_receipt_id": str(orm.payment_receipt_id) if orm.payment_receipt_id else None,
    }