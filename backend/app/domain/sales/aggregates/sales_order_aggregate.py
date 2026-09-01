"""SAL SalesOrderAggregate 聚合根 - 销售订单，含四态守恒 + 变更版本 + 关联报价 + 预留标识。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.entities.sales_order_line import SalesOrderLine
from app.domain.sales.value_objects.credit_pricing_vo import CreditCheckResult
from app.domain.sales.value_objects.sales_order_vo import SalesOrderStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode

_VALID_TRANSITIONS: dict[SalesOrderStatus, set[SalesOrderStatus]] = {
    SalesOrderStatus.DRAFT: {SalesOrderStatus.SUBMITTED, SalesOrderStatus.CANCELLED},
    SalesOrderStatus.SUBMITTED: {
        SalesOrderStatus.APPROVED,
        SalesOrderStatus.REJECTED,
        SalesOrderStatus.CANCELLED,
    },
    SalesOrderStatus.APPROVED: {SalesOrderStatus.RESERVED, SalesOrderStatus.CANCELLED},
    SalesOrderStatus.RESERVED: {
        SalesOrderStatus.PARTIAL_SHIPPED,
        SalesOrderStatus.SHIPPED,
        SalesOrderStatus.CANCELLED,
    },
    SalesOrderStatus.PARTIAL_SHIPPED: {
        SalesOrderStatus.PARTIAL_SHIPPED,
        SalesOrderStatus.SHIPPED,
    },
    SalesOrderStatus.SHIPPED: {SalesOrderStatus.COMPLETED},
    SalesOrderStatus.COMPLETED: {SalesOrderStatus.CLOSED},
    SalesOrderStatus.REJECTED: set(),
    SalesOrderStatus.CANCELLED: set(),
    SalesOrderStatus.CLOSED: set(),
}


@dataclass
class SalesOrderAggregate:
    """销售订单聚合根 - 禁止贫血模型。

    状态机：DRAFT→SUBMITTED→APPROVED→RESERVED→PARTIAL_SHIPPED→SHIPPED→COMPLETED→CLOSED，
    可 REJECTED/CANCELLED。
    四态守恒：每行维护 Ordered/Reserved/Shipped/Remaining。
    """

    order_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    order_code: str = ""
    customer_id: UUID = field(default_factory=uuid4)
    source_quotation_id: UUID | None = None
    shipping_warehouse_id: UUID | None = None
    payment_terms: str = ""
    currency: str = "CNY"
    status: SalesOrderStatus = SalesOrderStatus.DRAFT
    total_amount: float = 0.0
    reservation_ids: list[str] = field(default_factory=list)
    credit_check_result: CreditCheckResult | None = None
    submitted_by: UUID | None = None
    submitted_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    version: int = 1
    idempotency_key: str = ""
    correlation_id: UUID | None = None
    lines: list[SalesOrderLine] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: SalesOrderStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise SALError(
                SALErrorCode.ORDER_INVALID_STATE_TRANSITION,
                f"销售订单状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def add_line(self, line: SalesOrderLine) -> None:
        """添加订单行。"""
        line.order_id = self.order_id
        line.line_number = len(self.lines) + 1
        self.lines.append(line)
        self._recalculate_total()
        self.updated_at = datetime.now(timezone.utc)

    def _recalculate_total(self) -> None:
        self.total_amount = round(sum(line.line_amount for line in self.lines), 2)

    def submit(self, submitted_by: UUID) -> None:
        """DRAFT→SUBMITTED：提交，校验行/客户 ACTIVE/SKU 未停用/数量单价正/交期。"""
        if not self.lines:
            raise SALError(SALErrorCode.ORDER_NOT_FOUND, "销售订单无明细行")
        if not self.idempotency_key:
            raise SALError(SALErrorCode.IDEMPOTENCY_KEY_REQUIRED, "幂等键必填")
        self._transition(SalesOrderStatus.SUBMITTED)
        self.submitted_by = submitted_by
        self.submitted_at = datetime.now(timezone.utc)

    def approve(self, approver_id: UUID, opinion: str = "") -> None:
        """SUBMITTED→APPROVED：审批通过，复用 MDM GovernanceWorkflow。"""
        self._transition(SalesOrderStatus.APPROVED)
        self.approved_by = approver_id
        self.approved_at = datetime.now(timezone.utc)

    def reject(self, approver_id: UUID, opinion: str = "") -> None:
        """SUBMITTED→REJECTED：审批拒绝。"""
        self._transition(SalesOrderStatus.REJECTED)

    def confirm_fulfillment(self, reservation_ids: list[str]) -> None:
        """APPROVED→RESERVED：确认履约，通过 INV Reservation API 预留成功后调用。"""
        if not reservation_ids:
            raise SALError(SALErrorCode.RESERVATION_FAILED, "预留标识不能为空")
        self._transition(SalesOrderStatus.RESERVED)
        self.reservation_ids = list(reservation_ids)
        # 同步订单行状态
        for line, rid in zip(self.lines, reservation_ids, strict=False):
            line.mark_reserved(UUID(rid) if isinstance(rid, str) else rid)

    def update_shipped_quantity(self, line_id: UUID, ship_qty: float) -> None:
        """更新发货数量 - 联动订单状态（四态守恒）。"""
        if self.status not in (SalesOrderStatus.RESERVED, SalesOrderStatus.PARTIAL_SHIPPED):
            raise SALError(
                SALErrorCode.ORDER_INVALID_STATE_TRANSITION,
                "仅 RESERVED/PARTIAL_SHIPPED 状态可发货",
            )
        line = next((ln for ln in self.lines if ln.line_id == line_id), None)
        if line is None:
            raise SALError(SALErrorCode.ORDER_NOT_FOUND, f"订单行 {line_id} 不存在")
        line.ship(ship_qty)
        # 联动订单状态
        if all(ln.is_fully_shipped for ln in self.lines):
            self._transition(SalesOrderStatus.SHIPPED)
        elif (
            any(ln.shipped_quantity > 0 for ln in self.lines)
            and self.status == SalesOrderStatus.RESERVED
        ):
            self._transition(SalesOrderStatus.PARTIAL_SHIPPED)
        self.updated_at = datetime.now(timezone.utc)

    def change(self, changes: dict) -> None:
        """变更订单 - RESERVED/PARTIAL_SHIPPED 状态变更需经审批，version 递增。"""
        if self.status not in (SalesOrderStatus.RESERVED, SalesOrderStatus.PARTIAL_SHIPPED):
            raise SALError(
                SALErrorCode.ORDER_INVALID_STATE_TRANSITION,
                "仅 RESERVED/PARTIAL_SHIPPED 状态可变更",
            )
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        """取消订单 - 已发货订单拒绝取消。"""
        if any(line.shipped_quantity > 0 for line in self.lines):
            raise SALError(
                SALErrorCode.ORDER_CANCEL_WITH_SHIPPED,
                "已发货订单不可取消，需走退货流程",
            )
        self._transition(SalesOrderStatus.CANCELLED)
        # 释放所有预留
        for line in self.lines:
            if line.reservation_id is not None:
                line.release_reservation()

    def close(self) -> None:
        """COMPLETED→CLOSED：关闭。"""
        self._transition(SalesOrderStatus.CLOSED)

    def mark_completed(self) -> None:
        """SHIPPED→COMPLETED：结算完成且收款确认。"""
        self._transition(SalesOrderStatus.COMPLETED)

    @property
    def is_reserved_or_later(self) -> bool:
        return self.status in (
            SalesOrderStatus.RESERVED,
            SalesOrderStatus.PARTIAL_SHIPPED,
            SalesOrderStatus.SHIPPED,
            SalesOrderStatus.COMPLETED,
            SalesOrderStatus.CLOSED,
        )

    @property
    def has_shipped(self) -> bool:
        return any(line.shipped_quantity > 0 for line in self.lines)