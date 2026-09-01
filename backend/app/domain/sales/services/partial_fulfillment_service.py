"""SAL PartialFulfillmentService 领域服务 - 部分发货状态管理，维护四态守恒。"""

from __future__ import annotations

from uuid import UUID

from app.domain.sales.aggregates.sales_order_aggregate import SalesOrderAggregate
from app.domain.sales.entities.sales_order_line import SalesOrderLine
from app.domain.sales.value_objects.sales_order_vo import FourStateQty
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


class PartialFulfillmentService:
    """部分发货状态管理服务。

    输入：(订单行, 本次发货数量)
    输出：更新后四态
    核心逻辑：校验发货不超未发量（ship_qty ≤ remaining）
            + 累计 shipped_quantity += ship_qty
            + 计算 remaining_quantity = ordered - shipped
            + 联动订单状态（全部发完→SHIPPED，部分→PARTIAL_SHIPPED）
            + 四态守恒校验。
    """

    @staticmethod
    def validate_and_ship(line: SalesOrderLine, ship_qty: float) -> FourStateQty:
        """校验并执行发货，返回更新后四态。"""
        if ship_qty <= 0:
            raise SALError(SALErrorCode.SHIPMENT_OVER_SHIPPED, "发货数量必须为正数")
        remaining = line.remaining_quantity
        if ship_qty > remaining + 0.01:
            raise SALError(
                SALErrorCode.SHIPMENT_OVER_SHIPPED,
                f"发货超过未发量: 本次 {ship_qty} > 剩余 {remaining}",
            )
        # 执行发货（line.ship 内部会做四态守恒校验）
        line.ship(ship_qty)
        return FourStateQty(
            ordered=line.ordered_quantity,
            reserved=line.reserved_quantity,
            shipped=line.shipped_quantity,
            remaining=line.remaining_quantity,
        )

    @staticmethod
    def apply_to_order(order: SalesOrderAggregate, line_id: UUID, ship_qty: float) -> None:
        """将部分发货应用到订单，联动订单状态。"""
        order.update_shipped_quantity(line_id, ship_qty)

    @staticmethod
    def verify_four_state_invariant(order: SalesOrderAggregate) -> None:
        """校验订单所有行的四态守恒不变量。"""
        for line in order.lines:
            FourStateQty(
                ordered=line.ordered_quantity,
                reserved=line.reserved_quantity,
                shipped=line.shipped_quantity,
                remaining=line.remaining_quantity,
            )