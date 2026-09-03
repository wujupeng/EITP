"""FIN 付款聚合根 - PaymentAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import PaymentMethod, PaymentStatus
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class PaymentAggregate:
    """付款聚合根 - 状态机驱动付款全生命周期。"""

    payment_id: UUID
    payment_no: str
    ap_voucher_no: str
    payment_amount: Money
    payment_method: PaymentMethod
    payment_account: str
    payee_account: str
    status: PaymentStatus
    approver_id: str | None
    approval_opinion: str | None
    bank_ref: str | None
    expected_payment_date: date | None
    actual_payment_date: date | None
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        payment_no: str,
        ap_voucher_no: str,
        payment_amount: Money,
        payment_method: PaymentMethod,
        payment_account: str,
        payee_account: str,
        tenant_id: UUID,
        expected_payment_date: date | None = None,
    ) -> PaymentAggregate:
        return cls(
            payment_id=uuid4(),
            payment_no=payment_no,
            ap_voucher_no=ap_voucher_no,
            payment_amount=payment_amount,
            payment_method=payment_method,
            payment_account=payment_account,
            payee_account=payee_account,
            status=PaymentStatus.DRAFT,
            approver_id=None,
            approval_opinion=None,
            bank_ref=None,
            expected_payment_date=expected_payment_date,
            actual_payment_date=None,
            tenant_id=tenant_id,
        )

    def _check_transition(self, expected: PaymentStatus) -> None:
        if self.status != expected:
            raise FINError(
                FINErrorCode.PAYMENT_INVALID_TRANSITION,
                f"payment {self.payment_no} invalid transition: "
                f"{self.status.value} -> expected {expected.value}",
            )

    def submit(self) -> PaymentAggregate:
        self._check_transition(PaymentStatus.DRAFT)
        return dataclass_replace(
            self,
            status=PaymentStatus.PENDING_APPROVAL,
            updated_at=datetime.now(timezone.utc),
        )

    def approve(
        self, approver_id: str, approval_opinion: str | None = None
    ) -> PaymentAggregate:
        self._check_transition(PaymentStatus.PENDING_APPROVAL)
        return dataclass_replace(
            self,
            status=PaymentStatus.APPROVED,
            approver_id=approver_id,
            approval_opinion=approval_opinion,
            updated_at=datetime.now(timezone.utc),
        )

    def reject(
        self, approver_id: str, approval_opinion: str | None = None
    ) -> PaymentAggregate:
        self._check_transition(PaymentStatus.PENDING_APPROVAL)
        return dataclass_replace(
            self,
            status=PaymentStatus.DRAFT,
            approver_id=approver_id,
            approval_opinion=approval_opinion,
            updated_at=datetime.now(timezone.utc),
        )

    def execute(self) -> PaymentAggregate:
        self._check_transition(PaymentStatus.APPROVED)
        return dataclass_replace(
            self,
            status=PaymentStatus.EXECUTING,
            updated_at=datetime.now(timezone.utc),
        )

    def bank_callback_success(
        self, bank_ref: str, actual_payment_date: date | None = None
    ) -> PaymentAggregate:
        self._check_transition(PaymentStatus.EXECUTING)
        return dataclass_replace(
            self,
            status=PaymentStatus.SUCCESS,
            bank_ref=bank_ref,
            actual_payment_date=actual_payment_date or date.today(),
            updated_at=datetime.now(timezone.utc),
        )

    def bank_callback_failed(self, reason: str | None = None) -> PaymentAggregate:
        self._check_transition(PaymentStatus.EXECUTING)
        return dataclass_replace(
            self,
            status=PaymentStatus.FAILED,
            approval_opinion=reason,
            updated_at=datetime.now(timezone.utc),
        )

    def cancel(self) -> PaymentAggregate:
        if self.status not in (
            PaymentStatus.DRAFT,
            PaymentStatus.PENDING_APPROVAL,
            PaymentStatus.FAILED,
        ):
            raise FINError(
                FINErrorCode.PAYMENT_CANCEL_FORBIDDEN,
                f"payment {self.payment_no} cannot cancel from {self.status.value}",
            )
        return dataclass_replace(
            self,
            status=PaymentStatus.CANCELLED,
            updated_at=datetime.now(timezone.utc),
        )