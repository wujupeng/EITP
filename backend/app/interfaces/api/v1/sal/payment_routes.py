"""收款管理路由 - design 2.3.2.6，收款确认触发信用释放。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import PaymentReceiptAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import PaymentConfirmRequest

router = APIRouter(prefix="/sal/payments", tags=["sal-payment"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.get("")
@require_permission("sal:payment:request")
async def list_payments(
    status: str | None = Query(None), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = PaymentReceiptAppSvc(session)
    items = await svc.list_payments(tenant_id, status, offset, limit)
    return [
        {"payment_receipt_id": str(p.payment_receipt_id), "settlement_id": str(p.settlement_id),
         "payment_amount": float(p.payment_amount), "payment_method": p.payment_method,
         "status": p.status, "payment_no": p.payment_no}
        for p in items
    ]


@router.post("/{payment_id}/confirm")
@require_permission("sal:payment:confirm")
async def confirm_payment(payment_id: UUID, req: PaymentConfirmRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = PaymentReceiptAppSvc(session)
    orm = await svc.confirm_payment(tenant_id, payment_id, req.payment_no, req.idempotency_key)
    await session.commit()
    return {"payment_receipt_id": str(orm.payment_receipt_id), "status": orm.status,
            "payment_no": orm.payment_no}