"""库存位置查询路由 - 多维度查询与 PDA 扫码。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.warehouse.inventory_position_app_svc import InventoryPositionAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext

router = APIRouter(prefix="/wms/inventory-positions", tags=["wms-inventory-position"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.get("")
@require_permission("wms:position:query")
async def query_positions(
    sku_id: UUID | None = Query(None),
    location_id: UUID | None = Query(None),
    warehouse_id: UUID | None = Query(None),
    inventory_status: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = InventoryPositionAppSvc(session)
    if sku_id is not None:
        return await svc.query_by_sku(tenant_id, sku_id, warehouse_id)
    if location_id is not None:
        return await svc.query_by_location(tenant_id, location_id)
    return []


@router.get("/by-location/{location_code}")
@require_permission("wms:position:query")
async def query_by_location_code(
    location_code: str,
    warehouse_id: UUID = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = InventoryPositionAppSvc(session)
    return await svc.query_by_location_code(tenant_id, warehouse_id, location_code)


@router.get("/aggregate")
@require_permission("wms:position:query")
async def aggregate_by_sku_warehouse(
    sku_id: UUID = Query(...),
    warehouse_id: UUID = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = InventoryPositionAppSvc(session)
    return await svc.aggregate_by_sku_warehouse(tenant_id, sku_id, warehouse_id)
