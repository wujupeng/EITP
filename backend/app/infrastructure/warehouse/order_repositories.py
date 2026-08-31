"""WMS 作业单据仓储 - 收货/上架/拣货/移库/发货。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.warehouse.models import (
    WmsPickingLineORM,
    WmsPickingTaskORM,
    WmsPutawayTaskORM,
    WmsReceivingLineORM,
    WmsReceivingOrderORM,
    WmsShippingLineORM,
    WmsShippingOrderORM,
    WmsTransferLineORM,
    WmsTransferOrderORM,
)


class ReceivingOrderRepository:
    """收货单仓储。"""

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, receiving_id: UUID
    ) -> WmsReceivingOrderORM | None:
        stmt = select(WmsReceivingOrderORM).where(
            WmsReceivingOrderORM.tenant_id == tenant_id,
            WmsReceivingOrderORM.receiving_id == receiving_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_source_document(
        self, session: AsyncSession, tenant_id: UUID, source_document_id: UUID
    ) -> WmsReceivingOrderORM | None:
        stmt = select(WmsReceivingOrderORM).where(
            WmsReceivingOrderORM.tenant_id == tenant_id,
            WmsReceivingOrderORM.source_document_id == source_document_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_status(
        self, session: AsyncSession, tenant_id: UUID, status: str
    ) -> list[WmsReceivingOrderORM]:
        stmt = select(WmsReceivingOrderORM).where(
            WmsReceivingOrderORM.tenant_id == tenant_id,
            WmsReceivingOrderORM.status == status,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsReceivingOrderORM) -> WmsReceivingOrderORM:
        session.add(orm)
        await session.flush()
        return orm

    async def save_line(self, session: AsyncSession, orm: WmsReceivingLineORM) -> WmsReceivingLineORM:
        session.add(orm)
        await session.flush()
        return orm

    async def list_lines(
        self, session: AsyncSession, tenant_id: UUID, receiving_id: UUID
    ) -> list[WmsReceivingLineORM]:
        stmt = select(WmsReceivingLineORM).where(
            WmsReceivingLineORM.tenant_id == tenant_id,
            WmsReceivingLineORM.receiving_id == receiving_id,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def update_line_received(
        self, session: AsyncSession, line_orm: WmsReceivingLineORM, received_qty: float
    ) -> None:
        line_orm.received_quantity = received_qty
        await session.flush()


class PutawayTaskRepository:
    """上架任务仓储。"""

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, putaway_id: UUID
    ) -> WmsPutawayTaskORM | None:
        stmt = select(WmsPutawayTaskORM).where(
            WmsPutawayTaskORM.tenant_id == tenant_id,
            WmsPutawayTaskORM.putaway_id == putaway_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_status(
        self, session: AsyncSession, tenant_id: UUID, status: str
    ) -> list[WmsPutawayTaskORM]:
        stmt = select(WmsPutawayTaskORM).where(
            WmsPutawayTaskORM.tenant_id == tenant_id,
            WmsPutawayTaskORM.status == status,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsPutawayTaskORM) -> WmsPutawayTaskORM:
        session.add(orm)
        await session.flush()
        return orm


class PickingTaskRepository:
    """拣货任务仓储。"""

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, picking_id: UUID
    ) -> WmsPickingTaskORM | None:
        stmt = select(WmsPickingTaskORM).where(
            WmsPickingTaskORM.tenant_id == tenant_id,
            WmsPickingTaskORM.picking_id == picking_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_status(
        self, session: AsyncSession, tenant_id: UUID, status: str
    ) -> list[WmsPickingTaskORM]:
        stmt = select(WmsPickingTaskORM).where(
            WmsPickingTaskORM.tenant_id == tenant_id,
            WmsPickingTaskORM.status == status,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsPickingTaskORM) -> WmsPickingTaskORM:
        session.add(orm)
        await session.flush()
        return orm

    async def save_line(self, session: AsyncSession, orm: WmsPickingLineORM) -> WmsPickingLineORM:
        session.add(orm)
        await session.flush()
        return orm

    async def list_lines(
        self, session: AsyncSession, tenant_id: UUID, picking_task_id: UUID
    ) -> list[WmsPickingLineORM]:
        stmt = select(WmsPickingLineORM).where(
            WmsPickingLineORM.tenant_id == tenant_id,
            WmsPickingLineORM.picking_task_id == picking_task_id,
        )
        return list((await session.execute(stmt)).scalars().all())


class TransferOrderRepository:
    """移库单仓储。"""

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, transfer_id: UUID
    ) -> WmsTransferOrderORM | None:
        stmt = select(WmsTransferOrderORM).where(
            WmsTransferOrderORM.tenant_id == tenant_id,
            WmsTransferOrderORM.transfer_id == transfer_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_status(
        self, session: AsyncSession, tenant_id: UUID, status: str
    ) -> list[WmsTransferOrderORM]:
        stmt = select(WmsTransferOrderORM).where(
            WmsTransferOrderORM.tenant_id == tenant_id,
            WmsTransferOrderORM.status == status,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsTransferOrderORM) -> WmsTransferOrderORM:
        session.add(orm)
        await session.flush()
        return orm

    async def save_line(self, session: AsyncSession, orm: WmsTransferLineORM) -> WmsTransferLineORM:
        session.add(orm)
        await session.flush()
        return orm

    async def list_lines(
        self, session: AsyncSession, tenant_id: UUID, transfer_order_id: UUID
    ) -> list[WmsTransferLineORM]:
        stmt = select(WmsTransferLineORM).where(
            WmsTransferLineORM.tenant_id == tenant_id,
            WmsTransferLineORM.transfer_order_id == transfer_order_id,
        )
        return list((await session.execute(stmt)).scalars().all())


class ShippingOrderRepository:
    """发货单仓储。"""

    async def get_by_id(
        self, session: AsyncSession, tenant_id: UUID, shipping_id: UUID
    ) -> WmsShippingOrderORM | None:
        stmt = select(WmsShippingOrderORM).where(
            WmsShippingOrderORM.tenant_id == tenant_id,
            WmsShippingOrderORM.shipping_id == shipping_id,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_status(
        self, session: AsyncSession, tenant_id: UUID, status: str
    ) -> list[WmsShippingOrderORM]:
        stmt = select(WmsShippingOrderORM).where(
            WmsShippingOrderORM.tenant_id == tenant_id,
            WmsShippingOrderORM.status == status,
        )
        return list((await session.execute(stmt)).scalars().all())

    async def save(self, session: AsyncSession, orm: WmsShippingOrderORM) -> WmsShippingOrderORM:
        session.add(orm)
        await session.flush()
        return orm

    async def save_line(self, session: AsyncSession, orm: WmsShippingLineORM) -> WmsShippingLineORM:
        session.add(orm)
        await session.flush()
        return orm

    async def list_lines(
        self, session: AsyncSession, tenant_id: UUID, shipping_order_id: UUID
    ) -> list[WmsShippingLineORM]:
        stmt = select(WmsShippingLineORM).where(
            WmsShippingLineORM.tenant_id == tenant_id,
            WmsShippingLineORM.shipping_order_id == shipping_order_id,
        )
        return list((await session.execute(stmt)).scalars().all())