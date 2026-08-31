"""WMS Inventory Position 仓储 - 物理库存分布面查询与变更。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.warehouse.models import WmsInventoryPositionORM


class InventoryPositionRepository:
    """库存位置仓储 - WMS 物理分布面，与 INV Balance 映射。"""

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, position_id: UUID
    ) -> WmsInventoryPositionORM | None:
        stmt = select(WmsInventoryPositionORM).where(
            WmsInventoryPositionORM.tenant_id == tenant_id,
            WmsInventoryPositionORM.position_id == position_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def query_by_sku(
        self, session: AsyncSession, tenant_id: UUID, sku_id: UUID, warehouse_id: UUID | None = None
    ) -> list[WmsInventoryPositionORM]:
        stmt = select(WmsInventoryPositionORM).where(
            WmsInventoryPositionORM.tenant_id == tenant_id,
            WmsInventoryPositionORM.sku_id == sku_id,
        )
        if warehouse_id is not None:
            stmt = stmt.where(WmsInventoryPositionORM.warehouse_id == warehouse_id)
        return list((await session.execute(stmt)).scalars().all())

    async def query_by_location(
        self, session: AsyncSession, tenant_id: UUID, location_id: UUID
    ) -> list[WmsInventoryPositionORM]:
        stmt = select(WmsInventoryPositionORM).where(
            WmsInventoryPositionORM.tenant_id == tenant_id,
            WmsInventoryPositionORM.location_id == location_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def query_by_sku_location_status(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
        location_id: UUID,
        inventory_status: str,
    ) -> WmsInventoryPositionORM | None:
        stmt = select(WmsInventoryPositionORM).where(
            WmsInventoryPositionORM.tenant_id == tenant_id,
            WmsInventoryPositionORM.sku_id == sku_id,
            WmsInventoryPositionORM.location_id == location_id,
            WmsInventoryPositionORM.inventory_status == inventory_status,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def aggregate_by_sku_warehouse(
        self, session: AsyncSession, tenant_id: UUID, sku_id: UUID, warehouse_id: UUID
    ) -> list[tuple[str, float]]:
        """按状态聚合 SKU 在仓库中的库存量（对账用）。"""
        stmt = (
            select(
                WmsInventoryPositionORM.inventory_status,
                func.sum(WmsInventoryPositionORM.quantity).label("total_qty"),
            )
            .where(
                WmsInventoryPositionORM.tenant_id == tenant_id,
                WmsInventoryPositionORM.sku_id == sku_id,
                WmsInventoryPositionORM.warehouse_id == warehouse_id,
            )
            .group_by(WmsInventoryPositionORM.inventory_status)
        )
        rows = (await session.execute(stmt)).all()
        return [(row.inventory_status, float(row.total_qty or 0)) for row in rows]

    async def upsert(self, session: AsyncSession, orm: WmsInventoryPositionORM) -> WmsInventoryPositionORM:
        session.add(orm)
        await session.flush()
        return orm

    async def adjust_quantity(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        position_id: UUID,
        delta: float,
    ) -> WmsInventoryPositionORM | None:
        stmt = select(WmsInventoryPositionORM).where(
            WmsInventoryPositionORM.tenant_id == tenant_id,
            WmsInventoryPositionORM.position_id == position_id,
        )
        orm = (await session.execute(stmt)).scalar_one_or_none()
        if orm is not None:
            orm.quantity = float(orm.quantity) + delta
            await session.flush()
        return orm