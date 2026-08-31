"""上架任务聚合根 - 从收货区/质检区上架到存储区。"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.warehouse.value_objects.wms_config import PutawayStrategy
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class PutawayStatus(str, Enum):
    PENDING = "pending"
    TARGET_SET = "target_set"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PutawayTaskAggregate(AggregateRoot):
    """上架任务聚合根 - 从收货区/质检区上架到存储区。

    上架通过 INV Transaction TRANSFER_OUT+TRANSFER_IN 落地。
    部分上架支持（spec 5.4.1.7）。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        source_location_id: UUID,
        sku_id: UUID,
        quantity: float,
        source_document_id: UUID,
        putaway_strategy: PutawayStrategy = PutawayStrategy.MANUAL,
        target_location_id: UUID | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._source_location_id = source_location_id
        self._target_location_id = target_location_id
        self._sku_id = sku_id
        self._quantity = quantity
        self._putaway_strategy = putaway_strategy
        self._source_document_id = source_document_id
        self._status = PutawayStatus.PENDING if target_location_id is None else PutawayStatus.TARGET_SET
        self._putaway_quantity: float = 0.0
        self._inv_transaction_ids: list[UUID] = []
        self._completed_at: datetime | None = None

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def source_location_id(self) -> UUID:
        return self._source_location_id

    @property
    def target_location_id(self) -> UUID | None:
        return self._target_location_id

    @property
    def sku_id(self) -> UUID:
        return self._sku_id

    @property
    def quantity(self) -> float:
        return self._quantity

    @property
    def putaway_strategy(self) -> PutawayStrategy:
        return self._putaway_strategy

    @property
    def source_document_id(self) -> UUID:
        return self._source_document_id

    @property
    def status(self) -> PutawayStatus:
        return self._status

    @property
    def putaway_quantity(self) -> float:
        return self._putaway_quantity

    @property
    def inv_transaction_ids(self) -> list[UUID]:
        return list(self._inv_transaction_ids)

    @property
    def remaining_quantity(self) -> float:
        return self._quantity - self._putaway_quantity

    def set_target_location(self, location_id: UUID) -> None:
        """设置目标库位（存储区）。"""
        if self._status not in (PutawayStatus.PENDING, PutawayStatus.TARGET_SET):
            raise WMSError(
                WMSErrorCode.PUTAWAY_ALREADY_COMPLETED,
                "上架任务已执行或已完成，不能设置目标库位",
            )
        self._target_location_id = location_id
        self._status = PutawayStatus.TARGET_SET
        self._touch()

    def execute(self, putaway_qty: float | None = None, idempotency_key: str | None = None) -> None:
        """执行上架 - 部分上架支持。"""
        if self._status != PutawayStatus.TARGET_SET:
            raise WMSError(
                WMSErrorCode.PUTAWAY_LOCATION_DISABLED,
                "未设置目标库位，不能执行上架",
            )
        qty = putaway_qty if putaway_qty is not None else self._quantity
        if qty < 0:
            raise WMSError(
                WMSErrorCode.SERVICE_UNAVAILABLE,
                "上架数量不能为负",
            )
        if self._putaway_quantity + qty > self._quantity + 1e-9:
            raise WMSError(
                WMSErrorCode.PUTAWAY_CAPACITY_EXCEEDED,
                f"上架数量超出任务量: 已上架 {self._putaway_quantity} + 本次 {qty} > 总量 {self._quantity}",
            )
        self._putaway_quantity += qty
        self._status = PutawayStatus.EXECUTING
        self._touch()

    def complete(self) -> None:
        """完成上架。"""
        if self._status != PutawayStatus.EXECUTING:
            raise WMSError(
                WMSErrorCode.PUTAWAY_ALREADY_COMPLETED,
                "上架任务未执行，不能完成",
            )
        self._status = PutawayStatus.COMPLETED
        self._completed_at = datetime.now(timezone.utc)
        self._touch()

    def cancel(self) -> None:
        """取消上架。"""
        if self._status in (PutawayStatus.COMPLETED, PutawayStatus.CANCELLED):
            raise WMSError(
                WMSErrorCode.PUTAWAY_ALREADY_COMPLETED,
                "上架任务已完成或已取消",
            )
        self._status = PutawayStatus.CANCELLED
        self._touch()