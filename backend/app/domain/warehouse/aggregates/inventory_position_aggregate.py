"""Inventory Position 聚合根 - WMS 物理执行面核心模型，反映货物物理分布。

与 INV Balance 映射但语义不同：INV Balance 是库存事实，WMS Position 是物理分布。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.warehouse.events.position_changed_event import PositionChangedEvent
from app.domain.warehouse.value_objects.batch_lot import BatchLot
from app.domain.warehouse.value_objects.inventory_status import (
    InventoryStatus,
    is_valid_transition,
)
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class InventoryPositionAggregate(AggregateRoot):
    """库存位置聚合根 - SKU × Location × Lot/Serial × InventoryStatus。

    组合键唯一：(tenant_id, sku_id, location_id, batch_number, lot_number, serial_number, inventory_status)
    禁止直接修改：所有变更必须通过 add_quantity/reduce_quantity/transfer_to/change_status 方法。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        location_id: UUID,
        quantity: float = 0,
        inventory_status: InventoryStatus = InventoryStatus.AVAILABLE,
        bin_id: UUID | None = None,
        batch_lot: BatchLot | None = None,
        received_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._sku_id = sku_id
        self._warehouse_id = warehouse_id
        self._location_id = location_id
        self._bin_id = bin_id
        self._batch_lot = batch_lot or BatchLot()
        self._quantity = quantity
        self._inventory_status = inventory_status
        self._received_at = received_at or datetime.now(timezone.utc)
        self._last_updated_at = datetime.now(timezone.utc)

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def sku_id(self) -> UUID:
        return self._sku_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def location_id(self) -> UUID:
        return self._location_id

    @property
    def bin_id(self) -> UUID | None:
        return self._bin_id

    @property
    def batch_lot(self) -> BatchLot:
        return self._batch_lot

    @property
    def quantity(self) -> float:
        return self._quantity

    @property
    def inventory_status(self) -> InventoryStatus:
        return self._inventory_status

    @property
    def received_at(self) -> datetime:
        return self._received_at

    @property
    def last_updated_at(self) -> datetime:
        return self._last_updated_at

    def composite_key(self) -> str:
        """组合键 - 用于唯一性校验。"""
        bl = self._batch_lot
        return (
            f"{self._tenant_id}|{self._sku_id}|{self._location_id}"
            f"|{bl.batch_number or ''}|{bl.lot_number or ''}|{bl.serial_number or ''}"
            f"|{self._inventory_status.value}"
        )

    def add_quantity(self, qty: float) -> None:
        """增加数量（收货/上架/移入）。"""
        if qty < 0:
            raise WMSError(
                WMSErrorCode.SERVICE_UNAVAILABLE,
                "增加数量不能为负",
            )
        before = {"quantity": self._quantity}
        self._quantity += qty
        self._last_updated_at = datetime.now(timezone.utc)
        self._touch()
        after = {"quantity": self._quantity}
        self._record_event(
            PositionChangedEvent(
                tenant_id=self._tenant_id,
                position_id=self._id.value,
                sku_id=self._sku_id,
                location_id=self._location_id,
                change_type="add_quantity",
                before_state=before,
                after_state=after,
            )
        )

    def reduce_quantity(self, qty: float) -> None:
        """减少数量（拣货/移出/发货）。"""
        if qty < 0:
            raise WMSError(
                WMSErrorCode.SERVICE_UNAVAILABLE,
                "减少数量不能为负",
            )
        if self._quantity - qty < 0:
            raise WMSError(
                WMSErrorCode.PICKING_INSUFFICIENT_AVAILABLE,
                f"库存位置数量不足: 当前 {self._quantity}, 减少 {qty}",
                details={
                    "position_id": str(self._id.value),
                    "current_qty": self._quantity,
                    "reduce_qty": qty,
                },
            )
        before = {"quantity": self._quantity}
        self._quantity -= qty
        self._last_updated_at = datetime.now(timezone.utc)
        self._touch()
        after = {"quantity": self._quantity}
        self._record_event(
            PositionChangedEvent(
                tenant_id=self._tenant_id,
                position_id=self._id.value,
                sku_id=self._sku_id,
                location_id=self._location_id,
                change_type="reduce_quantity",
                before_state=before,
                after_state=after,
            )
        )

    def transfer_to(self, new_location_id: UUID, new_bin_id: UUID | None = None) -> None:
        """转移到新库位（移库作业）。"""
        if new_location_id == self._location_id and new_bin_id == self._bin_id:
            return
        before = {"location_id": str(self._location_id), "bin_id": str(self._bin_id) if self._bin_id else None}
        self._location_id = new_location_id
        self._bin_id = new_bin_id
        self._last_updated_at = datetime.now(timezone.utc)
        self._touch()
        after = {"location_id": str(self._location_id), "bin_id": str(self._bin_id) if self._bin_id else None}
        self._record_event(
            PositionChangedEvent(
                tenant_id=self._tenant_id,
                position_id=self._id.value,
                sku_id=self._sku_id,
                location_id=new_location_id,
                change_type="transfer",
                before_state=before,
                after_state=after,
            )
        )

    def change_status(self, new_status: InventoryStatus) -> None:
        """变更库存状态（QC/冻结/解冻/隔离等）。"""
        if new_status == self._inventory_status:
            return
        if not is_valid_transition(self._inventory_status, new_status):
            raise WMSError(
                WMSErrorCode.TASK_INVALID_STATE_TRANSITION,
                f"库存状态流转不合法: {self._inventory_status.value} → {new_status.value}",
                details={
                    "position_id": str(self._id.value),
                    "from_status": self._inventory_status.value,
                    "to_status": new_status.value,
                },
            )
        before = {"inventory_status": self._inventory_status.value}
        self._inventory_status = new_status
        self._last_updated_at = datetime.now(timezone.utc)
        self._touch()
        after = {"inventory_status": self._inventory_status.value}
        self._record_event(
            PositionChangedEvent(
                tenant_id=self._tenant_id,
                position_id=self._id.value,
                sku_id=self._sku_id,
                location_id=self._location_id,
                change_type="status_change",
                before_state=before,
                after_state=after,
            )
        )