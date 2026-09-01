"""SAL SalesOrderLine 实体 - 订单行，四态守恒 Ordered/Reserved/Shipped/Remaining。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.value_objects.credit_pricing_vo import PricingMatchResult
from app.domain.sales.value_objects.sales_order_vo import (
    FourStateQty,
    SalesOrderLineStatus,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


@dataclass
class SalesOrderLine:
    """订单行实体 - SalesOrderAggregate 内部实体。

    四态守恒不变量：remaining = ordered - shipped，reserved ≥ shipped，shipped ≤ ordered。
    行金额 = ordered_quantity × unit_price，系统计算。
    """

    line_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    order_id: UUID = field(default_factory=uuid4)
    line_number: int = 0
    enterprise_sku_id: UUID = field(default_factory=uuid4)
    ordered_quantity: float = 0.0
    reserved_quantity: float = 0.0
    shipped_quantity: float = 0.0
    unit_price: float = 0.0
    expected_delivery_date: datetime | None = None
    pricing_match_result: PricingMatchResult | None = None
    reservation_id: UUID | None = None
    status: SalesOrderLineStatus = SalesOrderLineStatus.OPEN
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.ordered_quantity <= 0:
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, "订单数量必须为正数")
        if self.unit_price <= 0:
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, "订单单价必须为正数")
        # 校验四态守恒
        _ = self._four_state  # 触发不变量校验

    @property
    def _four_state(self) -> FourStateQty:
        return FourStateQty(
            ordered=self.ordered_quantity,
            reserved=self.reserved_quantity,
            shipped=self.shipped_quantity,
            remaining=round(self.ordered_quantity - self.shipped_quantity, 2),
        )

    @property
    def remaining_quantity(self) -> float:
        """剩余数量 = ordered - shipped，系统计算。"""
        return round(self.ordered_quantity - self.shipped_quantity, 2)

    @property
    def line_amount(self) -> float:
        """行金额 = ordered × unit_price，系统计算。"""
        return round(self.ordered_quantity * self.unit_price, 2)

    def mark_reserved(self, reservation_id: UUID) -> None:
        """标记为已预留。"""
        if self.status != SalesOrderLineStatus.OPEN:
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, "订单行非开放状态不可预留")
        self.reserved_quantity = self.ordered_quantity
        self.reservation_id = reservation_id
        self.status = SalesOrderLineStatus.RESERVED
        self.updated_at = datetime.now(timezone.utc)

    def ship(self, ship_qty: float) -> None:
        """累计发货数量 - 四态守恒校验。"""
        if ship_qty <= 0:
            raise SALError(SALErrorCode.SHIPMENT_OVER_SHIPPED, "发货数量必须为正数")
        new_shipped = round(self.shipped_quantity + ship_qty, 2)
        if new_shipped > self.ordered_quantity + 0.01:
            raise SALError(
                SALErrorCode.SHIPMENT_OVER_SHIPPED,
                f"发货超过订单量: 累计 {new_shipped} > 订单 {self.ordered_quantity}",
            )
        # 触发四态守恒校验
        FourStateQty(
            ordered=self.ordered_quantity,
            reserved=self.reserved_quantity,
            shipped=new_shipped,
            remaining=round(self.ordered_quantity - new_shipped, 2),
        )
        self.shipped_quantity = new_shipped
        if abs(new_shipped - self.ordered_quantity) < 0.01:
            self.status = SalesOrderLineStatus.SHIPPED
        else:
            self.status = SalesOrderLineStatus.PARTIAL_SHIPPED
        self.updated_at = datetime.now(timezone.utc)

    def release_reservation(self) -> None:
        """释放预留。"""
        if self.shipped_quantity > 0:
            raise SALError(SALErrorCode.ORDER_CANCEL_WITH_SHIPPED, "已发货订单行不可释放预留")
        self.reserved_quantity = 0.0
        self.reservation_id = None
        self.status = SalesOrderLineStatus.OPEN
        self.updated_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """取消订单行。"""
        if self.shipped_quantity > 0:
            raise SALError(SALErrorCode.ORDER_CANCEL_WITH_SHIPPED, "已发货订单行不可取消，需退货")
        self.status = SalesOrderLineStatus.CANCELLED
        self.reserved_quantity = 0.0
        self.reservation_id = None
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_fully_shipped(self) -> bool:
        return abs(self.shipped_quantity - self.ordered_quantity) < 0.01

    @property
    def is_partial_shipped(self) -> bool:
        return 0 < self.shipped_quantity < self.ordered_quantity