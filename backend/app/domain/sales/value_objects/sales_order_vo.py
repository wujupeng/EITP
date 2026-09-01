"""SAL 销售订单值对象 - SalesOrderStatus/SalesOrderLineStatus/FourStateQty。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.interfaces.middleware.error_handler import SALError, SALErrorCode


class SalesOrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESERVED = "reserved"
    PARTIAL_SHIPPED = "partial_shipped"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class SalesOrderLineStatus(str, Enum):
    OPEN = "open"
    RESERVED = "reserved"
    PARTIAL_SHIPPED = "partial_shipped"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class FourStateQty:
    """四态数量值对象 - 不变量：remaining = ordered - shipped 等。"""

    ordered: float
    reserved: float = 0.0
    shipped: float = 0.0
    remaining: float = 0.0

    def __post_init__(self) -> None:
        if self.ordered < 0:
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, "订单数量不可为负")
        if self.reserved < 0 or self.shipped < 0:
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, "预留/已发数量不可为负")
        expected_remaining = round(self.ordered - self.shipped, 2)
        if abs(self.remaining - expected_remaining) > 0.01:
            raise SALError(
                SALErrorCode.ORDER_INVALID_STATE_TRANSITION,
                f"四态守恒破坏: remaining({self.remaining}) != ordered({self.ordered})"
                f" - shipped({self.shipped})",
            )
        if self.reserved > self.ordered + 0.01:
            raise SALError(
                SALErrorCode.ORDER_INVALID_STATE_TRANSITION,
                f"预留超过订单量: reserved({self.reserved}) > ordered({self.ordered})",
            )
        if self.shipped > self.ordered + 0.01:
            raise SALError(
                SALErrorCode.ORDER_INVALID_STATE_TRANSITION,
                f"已发超过订单量: shipped({self.shipped}) > ordered({self.ordered})",
            )
        if self.shipped > self.reserved + 0.01:
            raise SALError(
                SALErrorCode.ORDER_INVALID_STATE_TRANSITION,
                f"已发超过预留: shipped({self.shipped}) > reserved({self.reserved})",
            )

    @classmethod
    def create(cls, ordered: float) -> FourStateQty:
        return cls(ordered=ordered, reserved=0.0, shipped=0.0, remaining=ordered)

    def with_reserved(self, reserved: float) -> FourStateQty:
        return FourStateQty(ordered=self.ordered, reserved=reserved, shipped=self.shipped)

    def with_shipped(self, shipped: float) -> FourStateQty:
        return FourStateQty(
            ordered=self.ordered,
            reserved=self.reserved,
            shipped=shipped,
            remaining=round(self.ordered - shipped, 2),
        )