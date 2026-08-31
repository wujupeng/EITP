"""发票管理路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session
from app.infrastructure.purchasing.models import PurInvoiceORM
from app.infrastructure.purchasing.repositories import InvoiceRepository
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import CreateInvoiceRequest, InvoiceMatchRequest

router = APIRouter(prefix="/pur/invoices", tags=["pur-invoice"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("")
@require_permission("pur:invoice:manage")
async def create_invoice(
    req: CreateInvoiceRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    orm = PurInvoiceORM(
        tenant_id=tenant_id, invoice_code=req.invoice_code,
        supplier_id=req.supplier_id, settlement_id=req.settlement_id,
        invoice_amount=req.invoice_amount, status="draft",
    )
    repo = InvoiceRepository()
    orm = await repo.save(session, orm)
    await session.commit()
    return {"invoice_id": str(orm.invoice_id), "invoice_code": orm.invoice_code, "status": orm.status}


@router.get("")
@require_permission("pur:invoice:manage")
async def list_invoices(
    supplier_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    stmt = select(PurInvoiceORM).where(PurInvoiceORM.tenant_id == tenant_id)
    if supplier_id:
        stmt = stmt.where(PurInvoiceORM.supplier_id == supplier_id)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {"invoice_id": str(i.invoice_id), "invoice_code": i.invoice_code,
         "supplier_id": str(i.supplier_id), "invoice_amount": float(i.invoice_amount),
         "status": i.status}
        for i in rows
    ]


@router.post("/{invoice_id}/match")
@require_permission("pur:invoice:manage")
async def match_settlement(
    invoice_id: UUID,
    req: InvoiceMatchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    repo = InvoiceRepository()
    orm = await repo.get_by_id(session, tenant_id, invoice_id)
    if orm is None:
        return {"error": "not_found"}
    orm.settlement_id = req.settlement_id
    orm.matched_amount = req.matched_amount
    orm.status = "matched"
    await session.flush()
    await session.commit()
    return {"invoice_id": str(orm.invoice_id), "settlement_id": str(orm.settlement_id), "status": orm.status}