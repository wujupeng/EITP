"""PUR 采购订单领域模型 - PurchaseOrder 聚合根 + 订单行实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    CHANGED = "changed"
    PARTIAL_RECEIVED = "partial_received"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class PurchaseOrderLine:
    line_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    ordered_quantity: float = 0.0
    received_quantity: float = 0.0
    unit_price: float = 0.0
    lead_time_days: int = 0
    remark: str = ""

    @property
    def is_fully_received(self) -> bool:
        return self.received_quantity >= self.ordered_quantity

    @property
    def line_amount(self) -> float:
        return self.ordered_quantity * self.unit_price


_VALID_TRANSITIONS: dict[PurchaseOrderStatus, set[PurchaseOrderStatus]] = {
    PurchaseOrderStatus.DRAFT: {PurchaseOrderStatus.SUBMITTED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.SUBMITTED: {PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.REJECTED},
    PurchaseOrderStatus.APPROVED: {PurchaseOrderStatus.SENT, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.SENT: {PurchaseOrderStatus.CHANGED, PurchaseOrderStatus.PARTIAL_RECEIVED, PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.CHANGED: {PurchaseOrderStatus.SENT, PurchaseOrderStatus.PARTIAL_RECEIVED, PurchaseOrderStatus.RECEIVED},
    PurchaseOrderStatus.PARTIAL_RECEIVED: {PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CLOSED},
    PurchaseOrderStatus.RECEIVED: {PurchaseOrderStatus.CLOSED},
    PurchaseOrderStatus.REJECTED: set(),
    PurchaseOrderStatus.CLOSED: set(),
    PurchaseOrderStatus.CANCELLED: set(),
}


@dataclass
class PurchaseOrderAggregate:
    order_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    order_code: str = ""
    supplier_id: UUID = field(default_factory=uuid4)
    warehouse_id: UUID | None = None
    request_id: UUID | None = None
    total_amount: float = 0.0
    lines: list[PurchaseOrderLine] = field(default_factory=list)
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    approved_by: UUID | None = None
    sent_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: PurchaseOrderStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise PURError(PURErrorCode.ORDER_INVALID_STATE_TRANSITION, f"采购订单状态非法流转: {self.status.value} → {target.value}")
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def submit(self) -> None:
        if not self.lines:
            raise PURError(PURErrorCode.ORDER_NOT_FOUND, "采购订单无明细行")
        self._transition(PurchaseOrderStatus.SUBMITTED)

    def approve(self, approver_id: UUID) -> None:
        self._transition(PurchaseOrderStatus.APPROVED)
        self.approved_by = approver_id

    def reject(self) -> None:
        self._transition(PurchaseOrderStatus.REJECTED)

    def send(self) -> None:
        self._transition(PurchaseOrderStatus.SENT)
        self.sent_at = datetime.now(timezone.utc)

    def change(self) -> None:
        self._transition(PurchaseOrderStatus.CHANGED)

    def cancel(self) -> None:
        if any(l.received_quantity > 0 for l in self.lines):
            raise PURError(PURErrorCode.ORDER_CANCEL_WITH_RECEIVED, "已收货订单不可取消")
        self._transition(PurchaseOrderStatus.CANCELLED)

    def close(self) -> None:
        self._transition(PurchaseOrderStatus.CLOSED)

    def receive(self, line_id: UUID, received_qty: float) -> None:
        line = next((l for l in self.lines if l.line_id == line_id), None)
        if line is None:
            raise PURError(PURErrorCode.ORDER_LINE_NOT_FOUND, f"订单行 {line_id} 不存在")
        line.received_quantity += received_qty
        if all(l.is_fully_received for l in self.lines):
            self._transition(PurchaseOrderStatus.RECEIVED)
        elif self.status in (PurchaseOrderStatus.SENT, PurchaseOrderStatus.CHANGED, PurchaseOrderStatus.PARTIAL_RECEIVED):
            self._transition(PurchaseOrderStatus.PARTIAL_RECEIVED)

    def add_line(self, line: PurchaseOrderLine) -> None:
        if line.ordered_quantity <= 0:
            raise PURError(PURErrorCode.ORDER_INVALID_STATE_TRANSITION, "订单数量必须为正数")
        self.lines.append(line)
        self.total_amount += line.line_amount

    @property
    def is_sent_or_later(self) -> bool:
        return self.status in (PurchaseOrderStatus.SENT, PurchaseOrderStatus.CHANGED, PurchaseOrderStatus.PARTIAL_RECEIVED, PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CLOSED)