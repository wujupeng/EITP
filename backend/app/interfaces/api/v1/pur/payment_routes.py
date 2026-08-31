"""付款申请路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.purchasing.pur_app_services import PaymentAppSvc
from app.infrastructure.db.session import get_db_session
from app.infrastructure.purchasing.models import PurPaymentRequestORM
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import PaymentConfirmRequest

router = APIRouter(prefix="/pur/payments", tags=["pur-payment"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.get("")
@require_permission("pur:payment:request")
async def list_payments(
    settlement_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    stmt = select(PurPaymentRequestORM).where(PurPaymentRequestORM.tenant_id == tenant_id)
    if settlement_id:
        stmt = stmt.where(PurPaymentRequestORM.settlement_id == settlement_id)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {"payment_id": str(p.payment_id), "payment_code": p.payment_code,
         "settlement_id": str(p.settlement_id), "amount": float(p.amount), "status": p.status}
        for p in rows
    ]


@router.post("/{payment_id}/confirm")
@require_permission("pur:payment:confirm")
async def confirm_payment(
    payment_id: UUID,
    req: PaymentConfirmRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = PaymentAppSvc(session)
    if not req.paid:
        orm = await svc._repo.get_by_id(session, tenant_id, payment_id)
        if orm:
            orm.status = "failed"
            await session.flush()
            await session.commit()
            return {"payment_id": str(orm.payment_id), "status": orm.status}
        return {"error": "not_found"}
    orm = await svc.complete_payment(tenant_id, payment_id)
    await session.commit()
    return {"payment_id": str(orm.payment_id), "status": orm.status}