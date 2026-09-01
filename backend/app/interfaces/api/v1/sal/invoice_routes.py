"""发票管理路由 - design 2.3.2.6。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import SalesInvoiceAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import CreateInvoiceRequest, InvoiceMatchRequest

router = APIRouter(prefix="/sal/invoices", tags=["sal-invoice"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("")
@require_permission("sal:invoice:create")
async def create_invoice(req: CreateInvoiceRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesInvoiceAppSvc(session)
    lines = [
        {"enterprise_sku_id": str(l.enterprise_sku_id), "quantity": l.quantity,
         "unit_price": l.unit_price, "tax_rate": l.tax_rate,
         "amount": l.quantity * l.unit_price, "tax_amount": l.quantity * l.unit_price * l.tax_rate}
        for l in req.lines
    ]
    orm = await svc.create_invoice(
        tenant_id, req.invoice_code, req.customer_id, req.invoice_amount, lines, req.tax_amount,
    )
    await session.commit()
    return {"invoice_id": str(orm.invoice_id), "invoice_code": orm.invoice_code, "status": orm.status}


@router.get("")
@require_permission("sal:invoice:create")
async def list_invoices(
    status: str | None = Query(None), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = SalesInvoiceAppSvc(session)
    items = await svc.list_invoices(tenant_id, status, offset, limit)
    return [
        {"invoice_id": str(i.invoice_id), "invoice_code": i.invoice_code,
         "customer_id": str(i.customer_id), "invoice_amount": float(i.invoice_amount),
         "status": i.status}
        for i in items
    ]


@router.post("/{invoice_id}/match")
@require_permission("sal:invoice:create")
async def match_invoice(invoice_id: UUID, req: InvoiceMatchRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = SalesInvoiceAppSvc(session)
    orm = await svc.match_settlement(tenant_id, invoice_id, req.settlement_id, req.matched_amount, req.diff_threshold)
    await session.commit()
    return {"invoice_id": str(orm.invoice_id), "status": orm.status,
            "matched_settlement_id": str(orm.matched_settlement_id) if orm.matched_settlement_id else None}