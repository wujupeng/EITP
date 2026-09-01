"""SAL SalesSettlementAggregate 聚合根 - 销售结算，通过 INV Financial/Revenue API 落地收入。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.entities.settlement_reconcile_line import SettlementReconcileLine
from app.domain.sales.value_objects.settlement_vo import SettlementStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode

_VALID_TRANSITIONS: dict[SettlementStatus, set[SettlementStatus]] = {
    SettlementStatus.PENDING: {SettlementStatus.RECONCILED},
    SettlementStatus.RECONCILED: {SettlementStatus.INVOICE_MATCHED},
    SettlementStatus.INVOICE_MATCHED: {SettlementStatus.PAYMENT_REQUESTED},
    SettlementStatus.PAYMENT_REQUESTED: {
        SettlementStatus.PAYMENT_COMPLETED,
        SettlementStatus.PAYMENT_REQUESTED,  # 收款失败可重新申请
    },
    SettlementStatus.PAYMENT_COMPLETED: set(),
}


@dataclass
class SalesSettlementAggregate:
    """销售结算聚合根 - 禁止贫血模型。

    状态机：PENDING→RECONCILED→INVOICE_MATCHED→PAYMENT_REQUESTED→PAYMENT_COMPLETED。
    对账明细校验（发货与订单行一致）+ 应收金额计算 + 差异阈值校验
    + 退货退款冲抵（净应收 = 应收 - 退款）
    + 通过 INV Financial/Revenue API 落地收入与成本结转（红线二）。
    """

    settlement_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    settlement_code: str = ""
    order_id: UUID = field(default_factory=uuid4)
    receivable_amount: float = 0.0
    refund_amount: float = 0.0
    net_receivable_amount: float = 0.0
    status: SettlementStatus = SettlementStatus.PENDING
    reconcile_lines: list[SettlementReconcileLine] = field(default_factory=list)
    invoice_id: UUID | None = None
    payment_receipt_id: UUID | None = None
    revenue_landed: bool = False
    idempotency_key: str = ""
    correlation_id: UUID | None = None
    reconciled_by: UUID | None = None
    reconciled_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: SettlementStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise SALError(
                SALErrorCode.SETTLEMENT_RECONCILE_DIFF_EXCEEDED,
                f"结算单状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def reconcile(
        self,
        lines: list[SettlementReconcileLine],
        threshold: float,
        reconciled_by: UUID,
    ) -> None:
        """对账：校对明细一致 + 差异校验 + 计算应收金额。"""
        if not lines:
            raise SALError(SALErrorCode.SETTLEMENT_NOT_FOUND, "对账明细不能为空")
        for line in lines:
            line.settlement_id = self.settlement_id
            if abs(line.diff) > threshold:
                raise SALError(
                    SALErrorCode.SETTLEMENT_RECONCILE_DIFF_EXCEEDED,
                    f"对账差异超阈值: diff={line.diff} > threshold={threshold}",
                )
        self.reconcile_lines = lines
        self.receivable_amount = round(sum(line.amount for line in lines), 2)
        self._update_net_receivable()
        self._transition(SettlementStatus.RECONCILED)
        self.reconciled_by = reconciled_by
        self.reconciled_at = datetime.now(timezone.utc)

    def match_invoice(self, invoice_id: UUID, invoice_amount: float, threshold: float) -> None:
        """匹配发票 - 差异阈值校验。"""
        if abs(invoice_amount - self.net_receivable_amount) > threshold:
            raise SALError(
                SALErrorCode.INVOICE_MATCH_DIFF_EXCEEDED,
                f"发票匹配差异超阈值: |{invoice_amount} - {self.net_receivable_amount}|"
                f" > {threshold}",
            )
        self._transition(SettlementStatus.INVOICE_MATCHED)
        self.invoice_id = invoice_id

    def request_payment(self, payment_receipt_id: UUID) -> None:
        """创建收款申请：INVOICE_MATCHED→PAYMENT_REQUESTED。"""
        self._transition(SettlementStatus.PAYMENT_REQUESTED)
        self.payment_receipt_id = payment_receipt_id

    def confirm_payment(self) -> None:
        """收款完成：PAYMENT_REQUESTED→PAYMENT_COMPLETED。"""
        self._transition(SettlementStatus.PAYMENT_COMPLETED)

    def apply_refund(self, refund_amount: float) -> None:
        """退货退款冲抵 - 净应收 = 应收 - 退款。"""
        if refund_amount < 0:
            raise SALError(SALErrorCode.SETTLEMENT_NOT_FOUND, "退款金额不可为负")
        self.refund_amount = round(self.refund_amount + refund_amount, 2)
        self._update_net_receivable()

    def mark_revenue_landed(self) -> None:
        """标记收入已通过 INV Financial/Revenue API 落地（红线二）。"""
        self.revenue_landed = True
        self.updated_at = datetime.now(timezone.utc)

    def _update_net_receivable(self) -> None:
        """净应收 = 应收 - 退款。"""
        self.net_receivable_amount = round(self.receivable_amount - self.refund_amount, 2)

    @property
    def is_reconciled(self) -> bool:
        return self.status in (
            SettlementStatus.RECONCILED,
            SettlementStatus.INVOICE_MATCHED,
            SettlementStatus.PAYMENT_REQUESTED,
            SettlementStatus.PAYMENT_COMPLETED,
        )