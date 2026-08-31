"""仓储空间管理路由 - 仓库/库区/区域/库位/料箱/设备。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.warehouse.space_app_svc import SpaceAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.wms import (
    CreateAreaRequest,
    CreateBinRequest,
    CreateEquipmentRequest,
    CreateLocationRequest,
    CreateWarehouseRequest,
    CreateZoneRequest,
    ToggleStatusRequest,
)

router = APIRouter(prefix="/wms/space", tags=["wms-space"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("/warehouses")
@require_permission("wms:space:manage")
async def create_warehouse(
    req: CreateWarehouseRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    orm = await svc.create_warehouse(
        tenant_id, req.warehouse_code, req.warehouse_name, req.address, req.hierarchy_node_id
    )
    await session.commit()
    return {"warehouse_id": str(orm.warehouse_id), "warehouse_code": orm.warehouse_code, "status": orm.status}


@router.post("/zones")
@require_permission("wms:space:manage")
async def create_zone(
    req: CreateZoneRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    orm = await svc.create_zone(
        tenant_id, req.warehouse_id, req.zone_code, req.zone_name, req.zone_function
    )
    await session.commit()
    return {"zone_id": str(orm.zone_id), "zone_code": orm.zone_code, "status": orm.status}


@router.get("/zones")
@require_permission("wms:space:query")
async def list_zones(
    warehouse_id: UUID = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    zones = await svc._zone_repo.list_by_warehouse(session, tenant_id, warehouse_id)
    return [
        {"zone_id": str(z.zone_id), "zone_code": z.zone_code, "zone_name": z.zone_name,
         "zone_function": z.zone_function, "status": z.status}
        for z in zones
    ]


@router.post("/areas")
@require_permission("wms:space:manage")
async def create_area(
    req: CreateAreaRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    orm = await svc.create_area(tenant_id, req.zone_id, req.area_code, req.area_name)
    await session.commit()
    return {"area_id": str(orm.area_id), "area_code": orm.area_code, "status": orm.status}


@router.post("/locations")
@require_permission("wms:space:manage")
async def create_location(
    req: CreateLocationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    orm = await svc.create_location(
        tenant_id, req.warehouse_id, req.zone_id, req.location_code,
        req.location_type, req.area_id, req.capacity_max_qty,
        req.capacity_max_weight, req.capacity_max_volume,
        req.capacity_enforce_mode, req.coordinate_x, req.coordinate_y, req.coordinate_z,
    )
    await session.commit()
    return {"location_id": str(orm.location_id), "location_code": orm.location_code, "status": orm.status}


@router.get("/locations")
@require_permission("wms:space:query")
async def list_locations(
    warehouse_id: UUID = Query(...),
    zone_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    if zone_id is not None:
        locs = await svc._loc_repo.list_by_zone(session, tenant_id, zone_id)
    else:
        locs = await svc._loc_repo.list_available_for_picking(session, tenant_id, warehouse_id)
    return [
        {"location_id": str(l.location_id), "location_code": l.location_code,
         "location_type": l.location_type, "status": l.status}
        for l in locs
    ]


@router.patch("/locations/{location_id}/status")
@require_permission("wms:space:manage")
async def toggle_location_status(
    location_id: UUID,
    req: ToggleStatusRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    orm = await svc.toggle_location_status(tenant_id, location_id, req.activate)
    await session.commit()
    return {"location_id": str(location_id), "status": orm.status if orm else None}


@router.get("/warehouses/{warehouse_id}/tree")
@require_permission("wms:space:query")
async def query_space_tree(
    warehouse_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    return await svc.query_space_tree(tenant_id, warehouse_id)


@router.post("/bins")
@require_permission("wms:space:manage")
async def create_bin(
    req: CreateBinRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    orm = await svc.create_bin(tenant_id, req.location_id, req.bin_code)
    await session.commit()
    return {"bin_id": str(orm.bin_id), "bin_code": orm.bin_code, "status": orm.status}


@router.post("/equipments")
@require_permission("wms:space:manage")
async def create_equipment(
    req: CreateEquipmentRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = SpaceAppSvc(session)
    orm = await svc.create_equipment(tenant_id, req.warehouse_id, req.equipment_code, req.equipment_type)
    await session.commit()
    return {"equipment_id": str(orm.equipment_id), "equipment_code": orm.equipment_code, "status": orm.status}
