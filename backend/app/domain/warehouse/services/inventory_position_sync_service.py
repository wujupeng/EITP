"""库存位置同步服务 - INV Transaction 执行后同步 WMS Inventory Position。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.warehouse.aggregates.inventory_position_aggregate import (
    InventoryPositionAggregate,
)
from app.domain.warehouse.value_objects.inventory_status import InventoryStatus


@dataclass(frozen=True)
class InvTransactionResult:
    """INV Transaction 执行结果 - 供 WMS 同步使用。"""
    transaction_id: UUID
    transaction_type: str
    sku_id: UUID
    warehouse_id: UUID
    location_id: UUID
    quantity: float
    direction: str


_TRANSACTION_TYPE_TO_WMS_STATUS: dict[str, InventoryStatus] = {
    "purchase_receipt": InventoryStatus.AVAILABLE,
    "sales_issue": InventoryStatus.AVAILABLE,
    "transfer_in": InventoryStatus.AVAILABLE,
    "transfer_out": InventoryStatus.IN_TRANSIT,
    "adjustment_in": InventoryStatus.AVAILABLE,
    "adjustment_out": InventoryStatus.AVAILABLE,
    "block": InventoryStatus.BLOCKED,
    "unblock": InventoryStatus.AVAILABLE,
    "inspection_in": InventoryStatus.IN_QC,
    "inspection_out": InventoryStatus.AVAILABLE,
}


class InventoryPositionSyncService:
    """库存位置同步领域服务 - 作业执行后同步 Inventory Position 与 INV Balance。

    红线：WMS Position 是物理分布面，INV Balance 是库存事实。
    本服务在 INV Transaction 成功后同步 WMS Position，不直接修改 INV 表。
    """

    @staticmethod
    def sync_after_inv_transaction(
        position: InventoryPositionAggregate,
        inv_result: InvTransactionResult,
    ) -> InventoryPositionAggregate:
        """INV Transaction 执行后同步 WMS Inventory Position。

        按 INV Transaction 类型映射 WMS InventoryStatus 与数量增减。
        """
        wms_status = _TRANSACTION_TYPE_TO_WMS_STATUS.get(
            inv_result.transaction_type, InventoryStatus.AVAILABLE
        )

        if wms_status != position.inventory_status:
            position.change_status(wms_status)

        if inv_result.direction == "INBOUND":
            position.add_quantity(inv_result.quantity)
        elif inv_result.direction == "OUTBOUND":
            position.reduce_quantity(inv_result.quantity)

        return position

    @staticmethod
    def sync_after_transfer(
        source_position: InventoryPositionAggregate,
        target_position: InventoryPositionAggregate,
        quantity: float,
        new_location_id: UUID,
    ) -> tuple[InventoryPositionAggregate, InventoryPositionAggregate]:
        """移库作业后同步源位置和目标位置。"""
        source_position.reduce_quantity(quantity)
        target_position.add_quantity(quantity)
        if source_position.location_id != new_location_id:
            source_position.transfer_to(new_location_id)
        return source_position, target_position