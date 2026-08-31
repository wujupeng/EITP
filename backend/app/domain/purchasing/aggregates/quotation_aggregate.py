"""PUR QuotationAggregate 聚合根 - 报价单，含治理工作流审批 + 有效期。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.domain.purchasing.entities.quotation_line import QuotationLine
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class QuotationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    EXPIRED = "expired"


_VALID_TRANSITIONS: dict[QuotationStatus, set[QuotationStatus]] = {
    QuotationStatus.DRAFT: {QuotationStatus.SUBMITTED},
    QuotationStatus.SUBMITTED: {QuotationStatus.APPROVED, QuotationStatus.REJECTED},
    QuotationStatus.APPROVED: {QuotationStatus.PUBLISHED},
    QuotationStatus.PUBLISHED: {QuotationStatus.EXPIRED},
    QuotationStatus.REJECTED: set(),
    QuotationStatus.EXPIRED: set(),
}


@dataclass
class QuotationAggregate:
    """报价单聚合根。"""

    quotation_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    supplier_id: UUID = field(default_factory=uuid4)
    quotation_code: str = ""
    valid_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime | None = None
    payment_terms: str = ""
    lines: list[QuotationLine] = field(default_factory=list)
    status: QuotationStatus = QuotationStatus.DRAFT
    governance_state: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: QuotationStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise PURError(
                PURErrorCode.ORDER_INVALID_STATE_TRANSITION,
                f"报价单状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target

    def submit(self) -> None:
        if self.valid_until and self.valid_until < self.valid_from:
            raise PURError(PURErrorCode.SUPPLIER_SCOPE_MISMATCH, "有效期结束日期早于开始日期")
        self._transition(QuotationStatus.SUBMITTED)

    def approve(self) -> None:
        self._transition(QuotationStatus.APPROVED)

    def reject(self) -> None:
        self._transition(QuotationStatus.REJECTED)

    def publish(self) -> None:
        self._transition(QuotationStatus.PUBLISHED)

    def check_expiry(self, now: datetime | None = None) -> bool:
        if self.status != QuotationStatus.PUBLISHED:
            return False
        now = now or datetime.now(timezone.utc)
        if self.valid_until and now > self.valid_until:
            self._transition(QuotationStatus.EXPIRED)
            return True
        return False

    def add_line(self, line: QuotationLine) -> None:
        if line.unit_price <= 0:
            raise PURError(PURErrorCode.SUPPLIER_SCOPE_MISMATCH, "报价单价必须为正数")
        self.lines.append(line)

    @property
    def is_valid(self) -> bool:
        return self.status == QuotationStatus.PUBLISHED