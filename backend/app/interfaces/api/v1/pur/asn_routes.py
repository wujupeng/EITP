"""到货通知（ASN）路由。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session
from app.infrastructure.purchasing.models import PurAsnLineORM, PurAsnORM
from app.infrastructure.purchasing.repositories import AsnRepository
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import AsnArriveRequest, CreateAsnRequest

router = APIRouter(prefix="/pur/asns", tags=["pur-asn"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("")
@require_permission("pur:asn:manage")
async def create_asn(
    req: CreateAsnRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    orm = PurAsnORM(
        tenant_id=tenant_id, asn_code=req.asn_code, order_id=req.order_id,
        supplier_id=req.supplier_id, warehouse_id=req.warehouse_id, status="pending",
    )
    repo = AsnRepository()
    orm = await repo.save(session, orm)
    for line in req.lines:
        session.add(PurAsnLineORM(
            tenant_id=tenant_id, asn_id=orm.asn_id,
            order_line_id=line.get("order_line_id"), sku_id=line.get("sku_id"),
            expected_quantity=line.get("expected_quantity", 0),
        ))
    await session.flush()
    await session.commit()
    return {"asn_id": str(orm.asn_id), "asn_code": orm.asn_code, "status": orm.status}


@router.get("")
@require_permission("pur:asn:manage")
async def list_asns(
    order_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    stmt = select(PurAsnORM).where(PurAsnORM.tenant_id == tenant_id)
    if order_id:
        stmt = stmt.where(PurAsnORM.order_id == order_id)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {"asn_id": str(a.asn_id), "asn_code": a.asn_code, "order_id": str(a.order_id),
         "status": a.status}
        for a in rows
    ]


@router.post("/{asn_id}/arrive")
@require_permission("pur:asn:manage")
async def arrive_asn(
    asn_id: UUID,
    req: AsnArriveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    repo = AsnRepository()
    orm = await repo.get_by_id(session, tenant_id, asn_id)
    if orm is None:
        return {"error": "not_found"}
    orm.status = "arrived" if req.arrived else "pending"
    await session.flush()
    await session.commit()
    return {"asn_id": str(orm.asn_id), "status": orm.status}