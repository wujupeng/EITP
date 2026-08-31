"""WMS 空间管理仓储 - Warehouse/Zone/Area/Location/Bin/Equipment。

企业级表含 tenant_id，查询自动过滤租户。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.warehouse.models import (
    WmsAreaORM,
    WmsBinORM,
    WmsEquipmentORM,
    WmsLocationORM,
    WmsWarehouseORM,
    WmsZoneORM,
)


class WarehouseRepository:
    """仓库仓储 - 复用 MT-001 HierarchyNode 层级，叠加 WMS 配置。"""

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, warehouse_id: UUID) -> WmsWarehouseORM | None:
        stmt = select(WmsWarehouseORM).where(
            WmsWarehouseORM.tenant_id == tenant_id,
            WmsWarehouseORM.warehouse_id == warehouse_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, session: AsyncSession, tenant_id: UUID, warehouse_code: str) -> WmsWarehouseORM | None:
        stmt = select(WmsWarehouseORM).where(
            WmsWarehouseORM.tenant_id == tenant_id,
            WmsWarehouseORM.warehouse_code == warehouse_code,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_tenant(
        self, session: AsyncSession, tenant_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[WmsWarehouseORM]:
        stmt = (
            select(WmsWarehouseORM)
            .where(WmsWarehouseORM.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsWarehouseORM) -> WmsWarehouseORM:
        session.add(orm)
        await session.flush()
        return orm


class ZoneRepository:
    """库区仓储。"""

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, zone_id: UUID) -> WmsZoneORM | None:
        stmt = select(WmsZoneORM).where(
            WmsZoneORM.tenant_id == tenant_id,
            WmsZoneORM.zone_id == zone_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_code(
        self, session: AsyncSession, tenant_id: UUID, warehouse_id: UUID, zone_code: str
    ) -> WmsZoneORM | None:
        stmt = select(WmsZoneORM).where(
            WmsZoneORM.tenant_id == tenant_id,
            WmsZoneORM.warehouse_id == warehouse_id,
            WmsZoneORM.zone_code == zone_code,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_warehouse(
        self, session: AsyncSession, tenant_id: UUID, warehouse_id: UUID
    ) -> list[WmsZoneORM]:
        stmt = select(WmsZoneORM).where(
            WmsZoneORM.tenant_id == tenant_id,
            WmsZoneORM.warehouse_id == warehouse_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_function(
        self, session: AsyncSession, tenant_id: UUID, warehouse_id: UUID, zone_function: str
    ) -> list[WmsZoneORM]:
        stmt = select(WmsZoneORM).where(
            WmsZoneORM.tenant_id == tenant_id,
            WmsZoneORM.warehouse_id == warehouse_id,
            WmsZoneORM.zone_function == zone_function,
            WmsZoneORM.status == "active",
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsZoneORM) -> WmsZoneORM:
        session.add(orm)
        await session.flush()
        return orm


class AreaRepository:
    """区域仓储。"""

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, area_id: UUID) -> WmsAreaORM | None:
        stmt = select(WmsAreaORM).where(
            WmsAreaORM.tenant_id == tenant_id,
            WmsAreaORM.area_id == area_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_zone(self, session: AsyncSession, tenant_id: UUID, zone_id: UUID) -> list[WmsAreaORM]:
        stmt = select(WmsAreaORM).where(
            WmsAreaORM.tenant_id == tenant_id,
            WmsAreaORM.zone_id == zone_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsAreaORM) -> WmsAreaORM:
        session.add(orm)
        await session.flush()
        return orm


class LocationRepository:
    """库位仓储。"""

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, location_id: UUID) -> WmsLocationORM | None:
        stmt = select(WmsLocationORM).where(
            WmsLocationORM.tenant_id == tenant_id,
            WmsLocationORM.location_id == location_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_code(
        self, session: AsyncSession, tenant_id: UUID, warehouse_id: UUID, location_code: str
    ) -> WmsLocationORM | None:
        stmt = select(WmsLocationORM).where(
            WmsLocationORM.tenant_id == tenant_id,
            WmsLocationORM.warehouse_id == warehouse_id,
            WmsLocationORM.location_code == location_code,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_zone(self, session: AsyncSession, tenant_id: UUID, zone_id: UUID) -> list[WmsLocationORM]:
        stmt = select(WmsLocationORM).where(
            WmsLocationORM.tenant_id == tenant_id,
            WmsLocationORM.zone_id == zone_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_area(self, session: AsyncSession, tenant_id: UUID, area_id: UUID) -> list[WmsLocationORM]:
        stmt = select(WmsLocationORM).where(
            WmsLocationORM.tenant_id == tenant_id,
            WmsLocationORM.area_id == area_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_available_for_putaway(
        self, session: AsyncSession, tenant_id: UUID, warehouse_id: UUID
    ) -> list[WmsLocationORM]:
        stmt = select(WmsLocationORM).where(
            WmsLocationORM.tenant_id == tenant_id,
            WmsLocationORM.warehouse_id == warehouse_id,
            WmsLocationORM.status == "active",
            WmsLocationORM.location_type.in_(["floor", "shelf"]),
        )
        return list((await session.execute(stmt)).scalars().all())

    async def list_available_for_picking(
        self, session: AsyncSession, tenant_id: UUID, warehouse_id: UUID
    ) -> list[WmsLocationORM]:
        stmt = select(WmsLocationORM).where(
            WmsLocationORM.tenant_id == tenant_id,
            WmsLocationORM.warehouse_id == warehouse_id,
            WmsLocationORM.status == "active",
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsLocationORM) -> WmsLocationORM:
        session.add(orm)
        await session.flush()
        return orm


class BinRepository:
    """料箱仓储。"""

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, bin_id: UUID) -> WmsBinORM | None:
        stmt = select(WmsBinORM).where(
            WmsBinORM.tenant_id == tenant_id,
            WmsBinORM.bin_id == bin_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_location(self, session: AsyncSession, tenant_id: UUID, location_id: UUID) -> list[WmsBinORM]:
        stmt = select(WmsBinORM).where(
            WmsBinORM.tenant_id == tenant_id,
            WmsBinORM.location_id == location_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsBinORM) -> WmsBinORM:
        session.add(orm)
        await session.flush()
        return orm


class EquipmentRepository:
    """设备仓储。"""

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, equipment_id: UUID) -> WmsEquipmentORM | None:
        stmt = select(WmsEquipmentORM).where(
            WmsEquipmentORM.tenant_id == tenant_id,
            WmsEquipmentORM.equipment_id == equipment_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_warehouse(
        self, session: AsyncSession, tenant_id: UUID, warehouse_id: UUID
    ) -> list[WmsEquipmentORM]:
        stmt = select(WmsEquipmentORM).where(
            WmsEquipmentORM.tenant_id == tenant_id,
            WmsEquipmentORM.warehouse_id == warehouse_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsEquipmentORM) -> WmsEquipmentORM:
        session.add(orm)
        await session.flush()
        return orm