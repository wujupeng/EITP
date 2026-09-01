"""SAL SalesReturnAggregate 聚合根 - 销售退货，通过 WMS Receiving API 触发退货收货（红线一）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.entities.return_line import ReturnLine
from app.domain.sales.value_objects.sales_return_vo import (
    Disposition,
    QcResult,
    SalesReturnStatus,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode

_VALID_TRANSITIONS: dict[SalesReturnStatus, set[SalesReturnStatus]] = {
    SalesReturnStatus.DRAFT: {SalesReturnStatus.SUBMITTED, SalesReturnStatus.CANCELLED},
    SalesReturnStatus.SUBMITTED: {
        SalesReturnStatus.APPROVED,
        SalesReturnStatus.REJECTED,
        SalesReturnStatus.CANCELLED,
    },
    SalesReturnStatus.APPROVED: {SalesReturnStatus.RECEIVING, SalesReturnStatus.FAILED},
    SalesReturnStatus.RECEIVING: {SalesReturnStatus.QC_PENDING, SalesReturnStatus.FAILED},
    SalesReturnStatus.QC_PENDING: {SalesReturnStatus.COMPLETED},
    SalesReturnStatus.COMPLETED: set(),
    SalesReturnStatus.REJECTED: set(),
    SalesReturnStatus.FAILED: set(),
    SalesReturnStatus.CANCELLED: set(),
}


@dataclass
class SalesReturnAggregate:
    """销售退货聚合根 - 禁止贫血模型。

    状态机：DRAFT→SUBMITTED→APPROVED→RECEIVING→QC_PENDING→COMPLETED，可 REJECTED/FAILED/CANCELLED。
    退货收货通过 WMS Receiving API（红线一），不直接增加库存。
    退货数量校验：不超原发货可用量 = 已发 - 已退。
    """

    return_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    return_code: str = ""
    order_id: UUID = field(default_factory=uuid4)
    original_shipment_id: UUID = field(default_factory=uuid4)
    return_reason: str = ""
    refund_amount: float = 0.0
    status: SalesReturnStatus = SalesReturnStatus.DRAFT
    lines: list[ReturnLine] = field(default_factory=list)
    wms_receiving_id: UUID | None = None
    inv_transaction_ids: list[str] = field(default_factory=list)
    idempotency_key: str = ""
    correlation_id: UUID | None = None
    submitted_by: UUID | None = None
    submitted_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: SalesReturnStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise SALError(
                SALErrorCode.ORDER_INVALID_STATE_TRANSITION,
                f"销售退货状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def add_line(self, line: ReturnLine, available_qty: float) -> None:
        """添加退货行 - 校验退货数量 ≤ 原发货可用量（已发 - 已退）。"""
        if line.return_quantity > available_qty + 0.01:
            raise SALError(
                SALErrorCode.RETURN_OVER_RETURNED,
                f"退货超过可用量: 退货 {line.return_quantity} > 可用 {available_qty}",
            )
        line.return_id = self.return_id
        self.lines.append(line)
        self.refund_amount = round(self.refund_amount + line.refund_amount, 2)
        self.updated_at = datetime.now(timezone.utc)

    def submit(self, submitted_by: UUID) -> None:
        """DRAFT→SUBMITTED：提交。"""
        if not self.lines:
            raise SALError(SALErrorCode.RETURN_NOT_FOUND, "退货无明细行")
        if not self.idempotency_key:
            raise SALError(SALErrorCode.IDEMPOTENCY_KEY_REQUIRED, "幂等键必填")
        self._transition(SalesReturnStatus.SUBMITTED)
        self.submitted_by = submitted_by
        self.submitted_at = datetime.now(timezone.utc)

    def approve(self, approver_id: UUID, opinion: str = "") -> None:
        """SUBMITTED→APPROVED：审批通过，复用 MDM GovernanceWorkflow。"""
        self._transition(SalesReturnStatus.APPROVED)
        self.approved_by = approver_id
        self.approved_at = datetime.now(timezone.utc)

    def reject(self, approver_id: UUID, opinion: str = "") -> None:
        """SUBMITTED→REJECTED：审批拒绝。"""
        self._transition(SalesReturnStatus.REJECTED)

    def receive(self, wms_receiving_id: UUID, inv_transaction_ids: list[str]) -> None:
        """APPROVED→RECEIVING：执行退货收货，通过 WMS Receiving API（红线一）。

        WMS 内部调 INV RETURN_IN +inspection。
        """
        if self.status != SalesReturnStatus.APPROVED:
            raise SALError(SALErrorCode.RETURN_NOT_APPROVED, "退货非已审批状态不可收货")
        self._transition(SalesReturnStatus.RECEIVING)
        self.wms_receiving_id = wms_receiving_id
        self.inv_transaction_ids = list(inv_transaction_ids)

    def enter_qc_pending(self) -> None:
        """RECEIVING→QC_PENDING：收货完成，待 QC。"""
        self._transition(SalesReturnStatus.QC_PENDING)

    def record_qc(self, line_id: UUID, qc_result: QcResult) -> None:
        """录入 QC 结论。"""
        line = next((ln for ln in self.lines if ln.line_id == line_id), None)
        if line is None:
            raise SALError(SALErrorCode.RETURN_NOT_FOUND, f"退货行 {line_id} 不存在")
        line.record_qc(qc_result)

    def dispose(self, line_id: UUID, disposition: Disposition) -> None:
        """处置决策 - Restock/Quarantine/Scrap，通过 WMS/INV API 落地处置。"""
        line = next((ln for ln in self.lines if ln.line_id == line_id), None)
        if line is None:
            raise SALError(SALErrorCode.RETURN_NOT_FOUND, f"退货行 {line_id} 不存在")
        line.dispose(disposition)

    def complete(self) -> None:
        """QC_PENDING→COMPLETED：QC 结论录入 + 处置决策完成。"""
        if not all(ln.qc_result is not None and ln.disposition is not None for ln in self.lines):
            raise SALError(SALErrorCode.RETURN_NOT_APPROVED, "存在未完成 QC 或处置的退货行")
        self._transition(SalesReturnStatus.COMPLETED)

    def cancel(self) -> None:
        """DRAFT/SUBMITTED→CANCELLED：取消。"""
        self._transition(SalesReturnStatus.CANCELLED)

    def mark_failed(self) -> None:
        """任意状态→FAILED：WMS 收货失败。"""
        if self.status == SalesReturnStatus.COMPLETED:
            raise SALError(SALErrorCode.RETURN_RECEIVING_FAILED, "已完成状态不可标记失败")
        self.status = SalesReturnStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)

    @property
    def total_return_quantity(self) -> float:
        return round(sum(line.return_quantity for line in self.lines), 2)