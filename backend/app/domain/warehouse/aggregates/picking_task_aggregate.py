"""拣货任务聚合根 - 拣货作业的单据载体，支持多库位拆分。"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.warehouse.entities.picking_line import PickingLine
from app.domain.warehouse.value_objects.wms_config import PickingStrategy
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class PickingStatus(str, Enum):
    DRAFT = "draft"
    RESERVED = "reserved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PickingTaskAggregate(AggregateRoot):
    """拣货任务聚合根 - 拣货作业的单据载体。

    拣货通过 INV Transaction SALES_ISSUE/TRANSFER_OUT + Reservation 预占落地。
    支持多库位拆分（如需 100 但单库位仅 60，拆分为两库位）。
    部分拣货支持（spec 5.5.1.7）。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        source_order_id: UUID,
        source_order_type: str,
        warehouse_id: UUID,
        picking_strategy: PickingStrategy = PickingStrategy.FIFO,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._source_order_id = source_order_id
        self._source_order_type = source_order_type
        self._warehouse_id = warehouse_id
        self._picking_strategy = picking_strategy
        self._status = PickingStatus.DRAFT
        self._lines: list[PickingLine] = []
        self._reservation_id: UUID | None = None
        self._inv_transaction_ids: list[UUID] = []

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def source_order_id(self) -> UUID:
        return self._source_order_id

    @property
    def source_order_type(self) -> str:
        return self._source_order_type

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def picking_strategy(self) -> PickingStrategy:
        return self._picking_strategy

    @property
    def status(self) -> PickingStatus:
        return self._status

    @property
    def lines(self) -> list[PickingLine]:
        return list(self._lines)

    @property
    def reservation_id(self) -> UUID | None:
        return self._reservation_id

    @property
    def inv_transaction_ids(self) -> list[UUID]:
        return list(self._inv_transaction_ids)

    def add_line(
        self,
        sku_id: UUID,
        source_location_id: UUID,
        required_quantity: float,
        strategy: str = "fifo",
    ) -> PickingLine:
        """添加拣货行 - 支持多库位拆分。"""
        if self._status != PickingStatus.DRAFT:
            raise WMSError(
                WMSErrorCode.PICKING_ALREADY_COMPLETED,
                "非草稿状态不能添加拣货行",
            )
        line = PickingLine(
            picking_task_id=self._id.value,
            sku_id=sku_id,
            source_location_id=source_location_id,
            required_quantity=required_quantity,
            strategy=strategy,
        )
        self._lines.append(line)
        self._touch()
        return line

    def create_reservation(self, reservation_id: UUID) -> None:
        """创建库存预占（DRAFT→RESERVED）。"""
        if self._status != PickingStatus.DRAFT:
            raise WMSError(
                WMSErrorCode.PICKING_STATUS_UNAVAILABLE,
                "非草稿状态不能创建预占",
            )
        self._reservation_id = reservation_id
        self._status = PickingStatus.RESERVED
        self._touch()

    def execute_line(
        self,
        line_id: UUID,
        picked_qty: float,
        idempotency_key: str | None = None,
    ) -> PickingLine:
        """执行拣货行 - 部分拣货支持。"""
        if self._status not in (PickingStatus.RESERVED, PickingStatus.EXECUTING):
            raise WMSError(
                WMSErrorCode.PICKING_STATUS_UNAVAILABLE,
                "拣货任务未预占或已完成",
            )

        line = next((l for l in self._lines if l.line_id == line_id), None)
        if line is None:
            raise WMSError(
                WMSErrorCode.PICKING_NOT_FOUND,
                f"拣货行 {line_id} 不存在",
            )

        if line.picked_quantity + picked_qty > line.required_quantity + 1e-9:
            raise WMSError(
                WMSErrorCode.PICKING_QTY_MISMATCH,
                f"拣货数量超出需求量: 已拣 {line.picked_quantity} + 本次 {picked_qty} > 需求 {line.required_quantity}",
            )

        line.pick(picked_qty)
        self._status = PickingStatus.EXECUTING
        self._touch()
        return line

    def complete(self) -> None:
        """完成拣货。"""
        if self._status != PickingStatus.EXECUTING:
            raise WMSError(
                WMSErrorCode.PICKING_ALREADY_COMPLETED,
                "拣货任务未执行，不能完成",
            )
        self._status = PickingStatus.COMPLETED
        self._touch()

    def is_all_lines_picked(self) -> bool:
        return all(l.is_fully_picked for l in self._lines)