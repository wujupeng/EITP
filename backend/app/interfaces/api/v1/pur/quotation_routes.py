"""报价单管理路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session
from app.infrastructure.purchasing.models import PurQuotationLineORM, PurQuotationORM
from app.infrastructure.purchasing.repositories import QuotationRepository
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import ApproveRequest, CreateQuotationRequest

router = APIRouter(prefix="/pur/quotations", tags=["pur-quotation"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("")
@require_permission("pur:quotation:manage")
async def create_quotation(
    req: CreateQuotationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    orm = PurQuotationORM(
        tenant_id=tenant_id, supplier_id=req.supplier_id,
        quotation_code=req.quotation_code, payment_terms=req.payment_terms,
    )
    if req.valid_from:
        orm.valid_from = req.valid_from
    if req.valid_until:
        orm.valid_until = req.valid_until
    repo = QuotationRepository()
    orm = await repo.save(session, orm)
    for line in req.lines:
        session.add(PurQuotationLineORM(
            tenant_id=tenant_id, quotation_id=orm.quotation_id,
            sku_id=line.sku_id, unit_price=line.unit_price,
            lead_time_days=line.lead_time_days, min_order_qty=line.min_order_qty,
        ))
    await session.flush()
    await session.commit()
    return {"quotation_id": str(orm.quotation_id), "quotation_code": orm.quotation_code, "status": orm.status}


@router.get("")
@require_permission("pur:quotation:manage")
async def list_quotations(
    supplier_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    stmt = select(PurQuotationORM).where(PurQuotationORM.tenant_id == tenant_id)
    if supplier_id:
        stmt = stmt.where(PurQuotationORM.supplier_id == supplier_id)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {"quotation_id": str(q.quotation_id), "quotation_code": q.quotation_code,
         "supplier_id": str(q.supplier_id), "status": q.status}
        for q in rows
    ]


@router.post("/{quotation_id}/submit")
@require_permission("pur:quotation:manage")
async def submit_quotation(
    quotation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    repo = QuotationRepository()
    orm = await repo.get_by_id(session, tenant_id, quotation_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "submitted"
    orm.governance_state = "submitted"
    await session.flush()
    await session.commit()
    return {"quotation_id": str(orm.quotation_id), "status": orm.status}


@router.post("/{quotation_id}/approve")
@require_permission("pur:quotation:manage")
async def approve_quotation(
    quotation_id: UUID,
    req: ApproveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    repo = QuotationRepository()
    orm = await repo.get_by_id(session, tenant_id, quotation_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "approved" if req.approved else "draft"
    orm.governance_state = "approved" if req.approved else "rejected"
    await session.flush()
    await session.commit()
    return {"quotation_id": str(orm.quotation_id), "status": orm.status}


@router.post("/{quotation_id}/publish")
@require_permission("pur:quotation:manage")
async def publish_quotation(
    quotation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    repo = QuotationRepository()
    orm = await repo.get_by_id(session, tenant_id, quotation_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "active"
    await session.flush()
    await session.commit()
    return {"quotation_id": str(orm.quotation_id), "status": orm.status}