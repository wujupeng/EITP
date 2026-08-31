"""PUR 采购申请领域模型 - PurchaseRequest 聚合根 + 申请行实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class PurchaseRequestStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"
    CANCELLED = "cancelled"


@dataclass
class PurchaseRequestLine:
    line_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    quantity: float = 0.0
    unit_price: float | None = None
    remark: str = ""


_VALID_TRANSITIONS: dict[PurchaseRequestStatus, set[PurchaseRequestStatus]] = {
    PurchaseRequestStatus.DRAFT: {PurchaseRequestStatus.SUBMITTED, PurchaseRequestStatus.CANCELLED},
    PurchaseRequestStatus.SUBMITTED: {PurchaseRequestStatus.APPROVED, PurchaseRequestStatus.REJECTED},
    PurchaseRequestStatus.APPROVED: {PurchaseRequestStatus.CONVERTED, PurchaseRequestStatus.CANCELLED},
    PurchaseRequestStatus.REJECTED: set(),
    PurchaseRequestStatus.CONVERTED: set(),
    PurchaseRequestStatus.CANCELLED: set(),
}


@dataclass
class PurchaseRequestAggregate:
    request_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    request_code: str = ""
    title: str = ""
    department_id: UUID | None = None
    budget_id: UUID | None = None
    total_amount: float = 0.0
    lines: list[PurchaseRequestLine] = field(default_factory=list)
    status: PurchaseRequestStatus = PurchaseRequestStatus.DRAFT
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    converted_order_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: PurchaseRequestStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise PURError(PURErrorCode.ORDER_INVALID_STATE_TRANSITION, f"采购申请状态非法流转: {self.status.value} → {target.value}")
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def submit(self) -> None:
        if not self.lines:
            raise PURError(PURErrorCode.REQUEST_NOT_FOUND, "采购申请无明细行")
        self._transition(PurchaseRequestStatus.SUBMITTED)

    def approve(self, approver_id: UUID) -> None:
        self._transition(PurchaseRequestStatus.APPROVED)
        self.approved_by = approver_id
        self.approved_at = datetime.now(timezone.utc)

    def reject(self) -> None:
        self._transition(PurchaseRequestStatus.REJECTED)

    def convert(self, order_id: UUID) -> None:
        self._transition(PurchaseRequestStatus.CONVERTED)
        self.converted_order_id = order_id

    def cancel(self) -> None:
        self._transition(PurchaseRequestStatus.CANCELLED)

    def add_line(self, line: PurchaseRequestLine) -> None:
        if line.quantity <= 0:
            raise PURError(PURErrorCode.REQUEST_BUDGET_EXCEEDED, "申请数量必须为正数")
        self.lines.append(line)
        if line.unit_price:
            self.total_amount += line.quantity * line.unit_price

    @property
    def is_approved(self) -> bool:
        return self.status == PurchaseRequestStatus.APPROVED