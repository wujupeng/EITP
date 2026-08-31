"""收货单聚合根 - 收货作业的单据载体。"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.warehouse.entities.receiving_line import ReceivingLine
from app.domain.warehouse.services.receiving_qty_validator import ReceivingQtyValidator
from app.domain.warehouse.value_objects.batch_lot import BatchLot
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class ReceivingStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    EXECUTING = "executing"
    COMPLETED = "completed"


class ReceivingOrderAggregate(AggregateRoot):
    """收货单聚合根 - 收货作业的单据载体。

    收货通过 INV Transaction PURCHASE_RECEIPT 落地。
    部分收货支持，免检商品直接 AVAILABLE。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        source_document_id: UUID,
        source_document_type: str,
        warehouse_id: UUID,
        zone_id: UUID,
        over_receive_ratio: float = 0.0,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._source_document_id = source_document_id
        self._source_document_type = source_document_type
        self._warehouse_id = warehouse_id
        self._zone_id = zone_id
        self._status = ReceivingStatus.DRAFT
        self._over_receive_ratio = over_receive_ratio
        self._lines: list[ReceivingLine] = []
        self._inv_transaction_ids: list[UUID] = []

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def source_document_id(self) -> UUID:
        return self._source_document_id

    @property
    def source_document_type(self) -> str:
        return self._source_document_type

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def status(self) -> ReceivingStatus:
        return self._status

    @property
    def lines(self) -> list[ReceivingLine]:
        return list(self._lines)

    @property
    def inv_transaction_ids(self) -> list[UUID]:
        return list(self._inv_transaction_ids)

    def add_line(
        self,
        sku_id: UUID,
        ordered_quantity: float,
        is_inspection_required: bool = True,
    ) -> ReceivingLine:
        """添加收货行。"""
        if self._status != ReceivingStatus.DRAFT:
            raise WMSError(
                WMSErrorCode.RECEIVING_ALREADY_COMPLETED,
                "非草稿状态不能添加收货行",
            )
        line = ReceivingLine(
            receiving_id=self._id.value,
            sku_id=sku_id,
            ordered_quantity=ordered_quantity,
            is_inspection_required=is_inspection_required,
        )
        self._lines.append(line)
        self._touch()
        return line

    def submit(self) -> None:
        """提交收货单（DRAFT→SUBMITTED）。"""
        if self._status != ReceivingStatus.DRAFT:
            raise WMSError(
                WMSErrorCode.RECEIVING_ALREADY_COMPLETED,
                "非草稿状态不能提交",
            )
        if not self._lines:
            raise WMSError(
                WMSErrorCode.SERVICE_UNAVAILABLE,
                "收货单无收货行，不能提交",
            )
        self._status = ReceivingStatus.SUBMITTED
        self._touch()

    def execute_line(
        self,
        line_id: UUID,
        received_qty: float,
        location_id: UUID | None = None,
        batch_lot: BatchLot | None = None,
        idempotency_key: str | None = None,
    ) -> ReceivingLine:
        """执行收货行 - 收货并校验数量。

        部分收货支持，免检商品直接 AVAILABLE。
        """
        if self._status not in (ReceivingStatus.SUBMITTED, ReceivingStatus.EXECUTING):
            raise WMSError(
                WMSErrorCode.RECEIVING_ALREADY_COMPLETED,
                "收货单未提交或已完成",
            )

        line = next((l for l in self._lines if l.line_id == line_id), None)
        if line is None:
            raise WMSError(
                WMSErrorCode.RECEIVING_NOT_FOUND,
                f"收货行 {line_id} 不存在",
            )

        ReceivingQtyValidator.validate(
            ordered_qty=line.ordered_quantity,
            received_qty=line.received_quantity,
            current_qty=received_qty,
            over_receive_ratio=self._over_receive_ratio,
        )

        line.receive(received_qty, location_id)
        if batch_lot is not None:
            line.batch_lot = batch_lot

        self._status = ReceivingStatus.EXECUTING
        self._touch()
        return line

    def complete(self) -> None:
        """完成收货单（EXECUTING→COMPLETED）。"""
        if self._status != ReceivingStatus.EXECUTING:
            raise WMSError(
                WMSErrorCode.RECEIVING_ALREADY_COMPLETED,
                "收货单未执行，不能完成",
            )
        self._status = ReceivingStatus.COMPLETED
        self._touch()

    def is_all_lines_received(self) -> bool:
        """所有行是否已全部收货。"""
        return all(l.is_fully_received for l in self._lines)