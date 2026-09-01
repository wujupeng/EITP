"""包装管理路由 - design 2.3.2.4。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import PackingAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import CreatePackingRequest

router = APIRouter(prefix="/sal/shipments", tags=["sal-packing"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("/{shipment_id}/packing")
@require_permission("sal:packing:manage")
async def create_packing(shipment_id: UUID, req: CreatePackingRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = PackingAppSvc(session)
    lines = [
        {"shipment_line_id": str(l.shipment_line_id), "carton_no": l.carton_no,
         "packed_quantity": l.packed_quantity, "gross_weight": l.gross_weight,
         "net_weight": l.net_weight, "volume": l.volume}
        for l in req.lines
    ]
    orm = await svc.create_packing(
        tenant_id, shipment_id, lines, package_count=req.package_count,
        total_gross_weight=req.total_gross_weight, total_net_weight=req.total_net_weight,
        total_volume=req.total_volume,
    )
    await session.commit()
    return {"packing_id": str(orm.packing_id), "shipment_id": str(orm.shipment_id), "status": orm.status}


@router.get("/{shipment_id}/packing")
@require_permission("sal:packing:manage")
async def get_packing(shipment_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = PackingAppSvc(session)
    orm = await svc.get_packing(tenant_id, shipment_id)
    if orm is None:
        return {"error": "not_found"}
    return {
        "packing_id": str(orm.packing_id), "shipment_id": str(orm.shipment_id),
        "package_count": orm.package_count, "total_gross_weight": float(orm.total_gross_weight),
        "total_net_weight": float(orm.total_net_weight), "total_volume": float(orm.total_volume),
        "status": orm.status,
    }


@router.post("/{shipment_id}/packing/complete")
@require_permission("sal:packing:manage")
async def complete_packing(shipment_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = PackingAppSvc(session)
    orm = await svc.get_packing(tenant_id, shipment_id)
    if orm is None:
        return {"error": "not_found"}
    orm = await svc.complete_packing(tenant_id, orm.packing_id)
    await session.commit()
    return {"packing_id": str(orm.packing_id), "status": orm.status}