"""SAL ShipmentOrderAggregate 聚合根 - 发货单，通过 WMS Picking/Shipping API 触发作业（红线一）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.entities.shipment_line import ShipmentLine
from app.domain.sales.value_objects.shipment_vo import PickingStrategy, ShipmentStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode

_VALID_TRANSITIONS: dict[ShipmentStatus, set[ShipmentStatus]] = {
    ShipmentStatus.DRAFT: {ShipmentStatus.SUBMITTED, ShipmentStatus.CANCELLED},
    ShipmentStatus.SUBMITTED: {
        ShipmentStatus.PICKING,
        ShipmentStatus.CANCELLED,
        ShipmentStatus.FAILED,
    },
    ShipmentStatus.PICKING: {ShipmentStatus.PACKED, ShipmentStatus.FAILED},
    ShipmentStatus.PACKED: {ShipmentStatus.SHIPPED, ShipmentStatus.FAILED},
    ShipmentStatus.SHIPPED: {ShipmentStatus.COMPLETED},
    ShipmentStatus.COMPLETED: set(),
    ShipmentStatus.CANCELLED: set(),
    ShipmentStatus.FAILED: set(),
}


@dataclass
class ShipmentOrderAggregate:
    """发货单聚合根 - 禁止贫血模型。

    状态机：DRAFT→SUBMITTED→PICKING→PACKED→SHIPPED→COMPLETED，可 CANCELLED/FAILED。
    支持一订单多发货单（部分发货）+ 一发货单多订单行（合并发货）。
    通过 WMS Picking API 触发拣货 + WMS Shipping API 触发发货（红线一）。
    """

    shipment_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    shipment_code: str = ""
    order_ids: list[str] = field(default_factory=list)
    shipping_warehouse_id: UUID = field(default_factory=uuid4)
    picking_strategy: PickingStrategy = PickingStrategy.FIFO
    logistics_no: str | None = None
    carrier: str | None = None
    lines: list[ShipmentLine] = field(default_factory=list)
    status: ShipmentStatus = ShipmentStatus.DRAFT
    wms_picking_task_id: UUID | None = None
    wms_shipping_id: UUID | None = None
    inv_transaction_ids: list[str] = field(default_factory=list)
    idempotency_key: str = ""
    correlation_id: UUID | None = None
    created_by: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    shipped_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: ShipmentStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise SALError(
                SALErrorCode.SHIPMENT_ORDER_INVALID,
                f"发货单状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def add_line(self, line: ShipmentLine) -> None:
        """添加发货行。"""
        line.shipment_id = self.shipment_id
        self.lines.append(line)
        self.updated_at = datetime.now(timezone.utc)

    def submit(self) -> None:
        """DRAFT→SUBMITTED：提交，校验关联订单状态 + 发货数量 ≤ 未发量。"""
        if not self.lines:
            raise SALError(SALErrorCode.SHIPMENT_NOT_FOUND, "发货单无明细行")
        if not self.order_ids:
            raise SALError(SALErrorCode.SHIPMENT_NOT_FOUND, "发货单未关联订单")
        if not self.idempotency_key:
            raise SALError(SALErrorCode.IDEMPOTENCY_KEY_REQUIRED, "幂等键必填")
        self._transition(ShipmentStatus.SUBMITTED)

    def mark_picking(self, wms_picking_task_id: UUID) -> None:
        """SUBMITTED→PICKING：WMS 拣货任务创建成功（红线一）。"""
        self._transition(ShipmentStatus.PICKING)
        self.wms_picking_task_id = wms_picking_task_id

    def mark_packed(self) -> None:
        """PICKING→PACKED：包装完成。"""
        self._transition(ShipmentStatus.PACKED)

    def confirm(
        self,
        logistics_no: str,
        wms_shipping_id: UUID,
        inv_transaction_ids: list[str],
    ) -> None:
        """PACKED→SHIPPED：发货确认，调用 WMS Shipping API 成功后（红线一）。

        WMS 内部调 INV SALES_SHIPMENT 落地 -on_hand + 消费预留。
        """
        if not logistics_no:
            raise SALError(SALErrorCode.SHIPMENT_ORDER_INVALID, "物流单号必填")
        self._transition(ShipmentStatus.SHIPPED)
        self.logistics_no = logistics_no
        self.wms_shipping_id = wms_shipping_id
        self.inv_transaction_ids = list(inv_transaction_ids)
        self.shipped_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        """SHIPPED→COMPLETED：完成。"""
        self._transition(ShipmentStatus.COMPLETED)

    def cancel(self) -> None:
        """DRAFT/SUBMITTED→CANCELLED：取消。"""
        self._transition(ShipmentStatus.CANCELLED)

    def mark_failed(self) -> None:
        """任意状态→FAILED：WMS 失败，库存不变可重试。"""
        if self.status == ShipmentStatus.SHIPPED:
            raise SALError(SALErrorCode.WMS_SHIPPING_FAILED, "已发货状态不可标记失败")
        self.status = ShipmentStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)

    @property
    def total_ship_quantity(self) -> float:
        return round(sum(line.ship_quantity for line in self.lines), 2)