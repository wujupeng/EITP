"""发货单聚合根 - 发货作业的单据载体，含物流信息。"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.warehouse.entities.shipping_line import ShippingLine
from app.domain.warehouse.value_objects.logistics_info import LogisticsInfo
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class ShippingStatus(str, Enum):
    DRAFT = "draft"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ShippingOrderAggregate(AggregateRoot):
    """发货单聚合根 - 发货作业的单据载体。

    拣货已完成校验（spec 5.7.1.7，EITP_WMS_SHIPPING_PICKING_NOT_COMPLETED）。
    物流单号录入（spec 5.7.1.4）。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        source_order_id: UUID,
        warehouse_id: UUID,
        zone_id: UUID,
        picking_completed: bool = False,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._source_order_id = source_order_id
        self._warehouse_id = warehouse_id
        self._zone_id = zone_id
        self._status = ShippingStatus.DRAFT
        self._lines: list[ShippingLine] = []
        self._logistics_info = LogisticsInfo()
        self._picking_completed = picking_completed
        self._inv_transaction_ids: list[UUID] = []

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def source_order_id(self) -> UUID:
        return self._source_order_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def status(self) -> ShippingStatus:
        return self._status

    @property
    def lines(self) -> list[ShippingLine]:
        return list(self._lines)

    @property
    def logistics_info(self) -> LogisticsInfo:
        return self._logistics_info

    @property
    def inv_transaction_ids(self) -> list[UUID]:
        return list(self._inv_transaction_ids)

    def add_line(self, sku_id: UUID, quantity: float) -> ShippingLine:
        """添加发货行。"""
        if self._status != ShippingStatus.DRAFT:
            raise WMSError(
                WMSErrorCode.SHIPPING_ALREADY_COMPLETED,
                "非草稿状态不能添加发货行",
            )
        line = ShippingLine(
            shipping_order_id=self._id.value,
            sku_id=sku_id,
            quantity=quantity,
        )
        self._lines.append(line)
        self._touch()
        return line

    def execute(
        self,
        logistics_no: str,
        logistics_company: str,
        idempotency_key: str | None = None,
    ) -> None:
        """执行发货 - 录入物流单号，校验拣货已完成。"""
        if self._status != ShippingStatus.DRAFT:
            raise WMSError(
                WMSErrorCode.SHIPPING_ALREADY_COMPLETED,
                "发货单非草稿状态",
            )
        if not self._picking_completed:
            raise WMSError(
                WMSErrorCode.SHIPPING_PICKING_NOT_COMPLETED,
                "拣货未完成，不能发货",
            )
        if not logistics_no or not logistics_company:
            raise WMSError(
                WMSErrorCode.SHIPPING_ZONE_INVALID,
                "物流单号和物流公司不能为空",
            )
        self._logistics_info = LogisticsInfo(
            logistics_no=logistics_no,
            logistics_company=logistics_company,
            shipped_at=datetime.now(timezone.utc),
        )
        self._status = ShippingStatus.EXECUTING
        self._touch()

    def complete(self) -> None:
        """完成发货。"""
        if self._status != ShippingStatus.EXECUTING:
            raise WMSError(
                WMSErrorCode.SHIPPING_ALREADY_COMPLETED,
                "发货单未执行，不能完成",
            )
        self._status = ShippingStatus.COMPLETED
        self._touch()

    def mark_picking_completed(self) -> None:
        """标记拣货已完成。"""
        self._picking_completed = True
        self._touch()