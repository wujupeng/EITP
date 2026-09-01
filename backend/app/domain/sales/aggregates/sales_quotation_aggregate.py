"""SAL SalesQuotationAggregate 聚合根 - 销售报价单，含治理工作流审批 + 有效期 + 转单关系。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.entities.quotation_line import QuotationLine
from app.domain.sales.value_objects.sales_quotation_status import SalesQuotationStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode

_VALID_TRANSITIONS: dict[SalesQuotationStatus, set[SalesQuotationStatus]] = {
    SalesQuotationStatus.DRAFT: {SalesQuotationStatus.SUBMITTED, SalesQuotationStatus.CANCELLED},
    SalesQuotationStatus.SUBMITTED: {
        SalesQuotationStatus.APPROVED,
        SalesQuotationStatus.REJECTED,
        SalesQuotationStatus.CANCELLED,
    },
    SalesQuotationStatus.APPROVED: {
        SalesQuotationStatus.CONVERTED,
        SalesQuotationStatus.EXPIRED,
    },
    SalesQuotationStatus.REJECTED: set(),
    SalesQuotationStatus.CONVERTED: set(),
    SalesQuotationStatus.EXPIRED: set(),
    SalesQuotationStatus.CANCELLED: set(),
}


@dataclass
class SalesQuotationAggregate:
    """销售报价单聚合根 - 禁止贫血模型。

    状态机：DRAFT→SUBMITTED→APPROVED→CONVERTED/EXPIRED，可 REJECTED/CANCELLED。
    引用 MDM EnterpriseSKU（红线三）+ Customer 主数据。
    """

    quotation_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    quotation_code: str = ""
    customer_id: UUID = field(default_factory=uuid4)
    valid_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime | None = None
    payment_terms: str = ""
    currency: str = "CNY"
    lines: list[QuotationLine] = field(default_factory=list)
    status: SalesQuotationStatus = SalesQuotationStatus.DRAFT
    governance_state: str = "draft"
    converted_order_id: UUID | None = None
    submitted_by: UUID | None = None
    submitted_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.valid_until and self.valid_until < self.valid_from:
            raise SALError(SALErrorCode.QUOTATION_EXPIRED, "有效期结束日期早于开始日期")

    def _transition(self, target: SalesQuotationStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise SALError(
                SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION,
                f"报价单状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def add_line(self, line: QuotationLine) -> None:
        """添加报价行 - 校验 SKU 未停用/数量单价正/有效期。"""
        line.quotation_id = self.quotation_id
        self.lines.append(line)
        self.updated_at = datetime.now(timezone.utc)

    def submit(self, submitted_by: UUID) -> None:
        """DRAFT→SUBMITTED：提交，校验行明细完整性。"""
        if not self.lines:
            raise SALError(SALErrorCode.QUOTATION_NOT_FOUND, "报价单无明细行")
        self._transition(SalesQuotationStatus.SUBMITTED)
        self.governance_state = "submitted"
        self.submitted_by = submitted_by
        self.submitted_at = datetime.now(timezone.utc)

    def approve(self, approver_id: UUID, opinion: str = "") -> None:
        """SUBMITTED→APPROVED：审批通过，复用 MDM GovernanceWorkflow。"""
        self._transition(SalesQuotationStatus.APPROVED)
        self.governance_state = "approved"
        self.approved_by = approver_id
        self.approved_at = datetime.now(timezone.utc)

    def reject(self, approver_id: UUID, opinion: str = "") -> None:
        """SUBMITTED→REJECTED：审批拒绝。"""
        self._transition(SalesQuotationStatus.REJECTED)
        self.governance_state = "rejected"

    def convert_to_order(self) -> UUID:
        """APPROVED→CONVERTED：转销售订单，继承客户/行明细/单价/付款条件。"""
        if self.status != SalesQuotationStatus.APPROVED:
            raise SALError(SALErrorCode.QUOTATION_NOT_APPROVED, "仅已审批报价可转单")
        if self._is_expired():
            raise SALError(SALErrorCode.QUOTATION_EXPIRED, "已过期报价不可转单")
        order_id = uuid4()
        self._transition(SalesQuotationStatus.CONVERTED)
        self.converted_order_id = order_id
        return order_id

    def cancel(self) -> None:
        """DRAFT/SUBMITTED→CANCELLED：取消。"""
        self._transition(SalesQuotationStatus.CANCELLED)

    def check_expiry(self, now: datetime | None = None) -> bool:
        """过期自动标记 EXPIRED，不可转单。"""
        if self.status != SalesQuotationStatus.APPROVED:
            return False
        if self._is_expired(now):
            self._transition(SalesQuotationStatus.EXPIRED)
            return True
        return False

    def _is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return self.valid_until is not None and now > self.valid_until

    @property
    def total_amount(self) -> float:
        """报价总金额 = Σ 行金额。"""
        return round(sum(line.line_amount for line in self.lines), 2)

    @property
    def is_convertible(self) -> bool:
        return self.status == SalesQuotationStatus.APPROVED and not self._is_expired()