"""SAL PaymentReceiptAggregate 聚合根 - 收款申请，含信用释放。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.value_objects.customer_vo import BankAccount
from app.domain.sales.value_objects.settlement_vo import PaymentMethod, PaymentStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode

_VALID_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.REQUESTED: {
        PaymentStatus.COMPLETED,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
    },
    PaymentStatus.COMPLETED: set(),
    PaymentStatus.FAILED: set(),
    PaymentStatus.CANCELLED: set(),
}


@dataclass
class PaymentReceiptAggregate:
    """收款申请聚合根 - 禁止贫血模型。

    状态机：REQUESTED→COMPLETED/FAILED/CANCELLED。
    收款完成后触发信用额度释放（CreditControlService.release）。
    """

    payment_receipt_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    settlement_id: UUID = field(default_factory=uuid4)
    payment_amount: float = 0.0
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    payment_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bank_account: BankAccount = field(default_factory=BankAccount)
    status: PaymentStatus = PaymentStatus.REQUESTED
    payment_no: str | None = None
    requested_by: UUID | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.payment_amount <= 0:
            raise SALError(SALErrorCode.PAYMENT_NOT_FOUND, "收款金额必须为正数")

    def _transition(self, target: PaymentStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise SALError(
                SALErrorCode.PAYMENT_FAILED,
                f"收款状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def confirm(self, payment_no: str) -> None:
        """收款完成 - 触发信用额度释放（由调用方执行 CreditControlService.release）。"""
        if not payment_no:
            raise SALError(SALErrorCode.PAYMENT_FAILED, "收款单号必填")
        self._transition(PaymentStatus.COMPLETED)
        self.payment_no = payment_no
        self.completed_at = datetime.now(timezone.utc)

    def fail(self) -> None:
        """收款失败。"""
        self._transition(PaymentStatus.FAILED)

    def cancel(self) -> None:
        """取消收款。"""
        self._transition(PaymentStatus.CANCELLED)

    @property
    def is_completed(self) -> bool:
        return self.status == PaymentStatus.COMPLETED