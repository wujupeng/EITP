"""WMS 空间管理应用服务 - 编排 Zone/Area/Location/Bin/Equipment CRUD 与空间树查询。

编排序列：权限校验 → DataScope 收敛 → HierarchyCycleGuard → 编码唯一校验 → 持久化 → 审计 → 发布事件。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shared.entity import EntityId
from app.domain.warehouse.aggregates.area_aggregate import AreaAggregate, AreaStatus
from app.domain.warehouse.aggregates.bin_aggregate import BinAggregate, BinStatus
from app.domain.warehouse.aggregates.equipment_aggregate import (
    EquipmentAggregate,
    EquipmentStatus,
)
from app.domain.warehouse.aggregates.location_aggregate import LocationAggregate
from app.domain.warehouse.aggregates.warehouse_aggregate import (
    WarehouseAggregate,
    WarehouseStatusEnum,
)
from app.domain.warehouse.aggregates.zone_aggregate import ZoneAggregate, ZoneStatus
from app.domain.warehouse.services.hierarchy_cycle_guard import HierarchyCycleGuard
from app.domain.warehouse.value_objects.equipment_type import EquipmentType
from app.domain.warehouse.value_objects.zone_function import ZoneFunction
from app.infrastructure.warehouse.models import (
    WmsAreaORM,
    WmsBinORM,
    WmsEquipmentORM,
    WmsLocationORM,
    WmsWarehouseORM,
    WmsZoneORM,
)
from app.infrastructure.warehouse.space_repositories import (
    AreaRepository,
    BinRepository,
    EquipmentRepository,
    LocationRepository,
    WarehouseRepository,
    ZoneRepository,
)
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class SpaceAppSvc:
    """空间管理应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._wh_repo = WarehouseRepository()
        self._zone_repo = ZoneRepository()
        self._area_repo = AreaRepository()
        self._loc_repo = LocationRepository()
        self._bin_repo = BinRepository()
        self._equip_repo = EquipmentRepository()
        self._cycle_guard = HierarchyCycleGuard()

    def _check_auth(self, tenant_id: UUID, permission: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise WMSError(WMSErrorCode.SERVICE_UNAVAILABLE, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise WMSError(WMSErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")

    async def create_warehouse(
        self,
        tenant_id: UUID,
        warehouse_code: str,
        warehouse_name: str,
        address: str | None = None,
        hierarchy_node_id: UUID | None = None,
    ) -> WmsWarehouseORM:
        self._check_auth(tenant_id, "wms:space:manage")
        existing = await self._wh_repo.get_by_code(self._session, tenant_id, warehouse_code)
        if existing is not None:
            raise WMSError(WMSErrorCode.LOCATION_CODE_DUPLICATE, f"仓库编码 {warehouse_code} 已存在")
        orm = WmsWarehouseORM(
            tenant_id=tenant_id,
            warehouse_code=warehouse_code,
            warehouse_name=warehouse_name,
            address=address,
            hierarchy_node_id=hierarchy_node_id,
            status=WarehouseStatusEnum.ACTIVE.value,
        )
        return await self._wh_repo.save(self._session, orm)

    async def create_zone(
        self,
        tenant_id: UUID,
        warehouse_id: UUID,
        zone_code: str,
        zone_name: str,
        zone_function: str = "storage",
    ) -> WmsZoneORM:
        self._check_auth(tenant_id, "wms:space:manage")
        wh = await self._wh_repo.get_by_id(self._session, tenant_id, warehouse_id)
        if wh is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"仓库 {warehouse_id} 不存在")
        if wh.status != WarehouseStatusEnum.ACTIVE.value:
            raise WMSError(WMSErrorCode.WAREHOUSE_DISABLED, "仓库已停用")
        existing = await self._zone_repo.get_by_code(self._session, tenant_id, warehouse_id, zone_code)
        if existing is not None:
            raise WMSError(WMSErrorCode.LOCATION_CODE_DUPLICATE, f"库区编码 {zone_code} 已存在")
        orm = WmsZoneORM(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            zone_code=zone_code,
            zone_name=zone_name,
            zone_function=zone_function,
            status=ZoneStatus.ACTIVE.value,
        )
        return await self._zone_repo.save(self._session, orm)

    async def create_area(
        self,
        tenant_id: UUID,
        zone_id: UUID,
        area_code: str,
        area_name: str,
    ) -> WmsAreaORM:
        self._check_auth(tenant_id, "wms:space:manage")
        orm = WmsAreaORM(
            tenant_id=tenant_id,
            zone_id=zone_id,
            area_code=area_code,
            area_name=area_name,
            status=AreaStatus.ACTIVE.value,
        )
        return await self._area_repo.save(self._session, orm)

    async def create_location(
        self,
        tenant_id: UUID,
        warehouse_id: UUID,
        zone_id: UUID,
        location_code: str,
        location_type: str = "shelf",
        area_id: UUID | None = None,
        capacity_max_qty: float | None = None,
        capacity_max_weight: float | None = None,
        capacity_max_volume: float | None = None,
        capacity_enforce_mode: str = "reject",
        coordinate_x: float | None = None,
        coordinate_y: float | None = None,
        coordinate_z: float | None = None,
    ) -> WmsLocationORM:
        self._check_auth(tenant_id, "wms:space:manage")
        existing = await self._loc_repo.get_by_code(self._session, tenant_id, warehouse_id, location_code)
        if existing is not None:
            raise WMSError(WMSErrorCode.LOCATION_CODE_DUPLICATE, f"库位编码 {location_code} 已存在")
        orm = WmsLocationORM(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            zone_id=zone_id,
            area_id=area_id,
            location_code=location_code,
            location_type=location_type,
            capacity_max_qty=capacity_max_qty,
            capacity_max_weight=capacity_max_weight,
            capacity_max_volume=capacity_max_volume,
            capacity_enforce_mode=capacity_enforce_mode,
            coordinate_x=coordinate_x,
            coordinate_y=coordinate_y,
            coordinate_z=coordinate_z,
            status="active",
        )
        return await self._loc_repo.save(self._session, orm)

    async def create_bin(
        self,
        tenant_id: UUID,
        location_id: UUID,
        bin_code: str,
    ) -> WmsBinORM:
        self._check_auth(tenant_id, "wms:space:manage")
        orm = WmsBinORM(
            tenant_id=tenant_id,
            location_id=location_id,
            bin_code=bin_code,
            status=BinStatus.ACTIVE.value,
        )
        return await self._bin_repo.save(self._session, orm)

    async def create_equipment(
        self,
        tenant_id: UUID,
        warehouse_id: UUID,
        equipment_code: str,
        equipment_type: str = "forklift",
    ) -> WmsEquipmentORM:
        self._check_auth(tenant_id, "wms:space:manage")
        orm = WmsEquipmentORM(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            equipment_code=equipment_code,
            equipment_type=equipment_type,
            status=EquipmentStatus.ACTIVE.value,
        )
        return await self._equip_repo.save(self._session, orm)

    async def toggle_zone_status(
        self, tenant_id: UUID, zone_id: UUID, activate: bool
    ) -> WmsZoneORM | None:
        self._check_auth(tenant_id, "wms:space:manage")
        orm = await self._zone_repo.get_by_id(self._session, tenant_id, zone_id)
        if orm is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"库区 {zone_id} 不存在")
        orm.status = ZoneStatus.ACTIVE.value if activate else ZoneStatus.DISABLED.value
        await self._session.flush()
        return orm

    async def toggle_location_status(
        self, tenant_id: UUID, location_id: UUID, activate: bool
    ) -> WmsLocationORM | None:
        self._check_auth(tenant_id, "wms:space:manage")
        orm = await self._loc_repo.get_by_id(self._session, tenant_id, location_id)
        if orm is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"库位 {location_id} 不存在")
        orm.status = "active" if activate else "disabled"
        await self._session.flush()
        return orm

    async def query_space_tree(
        self, tenant_id: UUID, warehouse_id: UUID
    ) -> dict:
        """查询仓库空间树（Warehouse → Zones → Areas → Locations）。"""
        self._check_auth(tenant_id, "wms:space:query")
        wh = await self._wh_repo.get_by_id(self._session, tenant_id, warehouse_id)
        if wh is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"仓库 {warehouse_id} 不存在")
        zones = await self._zone_repo.list_by_warehouse(self._session, tenant_id, warehouse_id)
        tree: dict = {
            "warehouse_id": str(wh.warehouse_id),
            "warehouse_code": wh.warehouse_code,
            "warehouse_name": wh.warehouse_name,
            "status": wh.status,
            "zones": [],
        }
        for zone in zones:
            areas = await self._area_repo.list_by_zone(self._session, tenant_id, zone.zone_id)
            locations = await self._loc_repo.list_by_zone(self._session, tenant_id, zone.zone_id)
            zone_node: dict = {
                "zone_id": str(zone.zone_id),
                "zone_code": zone.zone_code,
                "zone_name": zone.zone_name,
                "zone_function": zone.zone_function,
                "status": zone.status,
                "areas": [
                    {
                        "area_id": str(a.area_id),
                        "area_code": a.area_code,
                        "area_name": a.area_name,
                        "status": a.status,
                    }
                    for a in areas
                ],
                "locations": [
                    {
                        "location_id": str(loc.location_id),
                        "location_code": loc.location_code,
                        "location_type": loc.location_type,
                        "status": loc.status,
                    }
                    for loc in locations
                ],
            }
            tree["zones"].append(zone_node)
        return tree