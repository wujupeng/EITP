"""FIN 应付凭证聚合根 - APVoucherAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import VoucherStatus
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class APVoucherAggregate:
    """应付凭证聚合根 - 金额守恒 payable = paid + unpaid。"""

    voucher_id: UUID
    voucher_no: str
    business_ref_type: str
    business_ref_id: str
    payable_amount: Money
    paid_amount: Money
    unpaid_amount: Money
    status: VoucherStatus
    payment_terms: str | None
    due_date: date | None
    is_overdue: bool
    overdue_days: int
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        voucher_no: str,
        business_ref_type: str,
        business_ref_id: str,
        payable_amount: Money,
        tenant_id: UUID,
        payment_terms: str | None = None,
        due_date: date | None = None,
    ) -> APVoucherAggregate:
        return cls(
            voucher_id=uuid4(),
            voucher_no=voucher_no,
            business_ref_type=business_ref_type,
            business_ref_id=business_ref_id,
            payable_amount=payable_amount,
            paid_amount=Money.zero(payable_amount.currency),
            unpaid_amount=payable_amount,
            status=VoucherStatus.OPEN,
            payment_terms=payment_terms,
            due_date=due_date,
            is_overdue=False,
            overdue_days=0,
            tenant_id=tenant_id,
        )

    def _check_balance(self) -> None:
        if not Money.is_ap_conserved(
            self.payable_amount, self.paid_amount, self.unpaid_amount
        ):
            raise FINError(
                FINErrorCode.AP_UNBALANCED,
                f"AP voucher {self.voucher_no} unbalanced: "
                f"payable={self.payable_amount} != "
                f"paid={self.paid_amount} + unpaid={self.unpaid_amount}",
            )

    def apply_payment(self, amount: Money) -> APVoucherAggregate:
        if amount > self.unpaid_amount:
            raise FINError(
                FINErrorCode.PAYMENT_EXCEED_AP,
                f"payment amount {amount} exceeds unpaid {self.unpaid_amount}",
            )
        new_paid = self.paid_amount.add(amount)
        new_unpaid = self.unpaid_amount.subtract(amount)
        if not Money.is_ap_conserved(
            self.payable_amount, new_paid, new_unpaid
        ):
            raise FINError(
                FINErrorCode.AP_UNBALANCED,
                f"AP voucher {self.voucher_no} unbalanced after payment",
            )
        zero = Money.zero(self.payable_amount.currency)
        if new_paid == self.payable_amount:
            status = VoucherStatus.SETTLED
        elif new_paid > zero:
            status = VoucherStatus.PARTIAL
        else:
            status = VoucherStatus.OPEN
        return dataclass_replace(
            self,
            paid_amount=new_paid,
            unpaid_amount=new_unpaid,
            status=status,
            updated_at=datetime.now(timezone.utc),
        )

    def mark_partial(self) -> APVoucherAggregate:
        return dataclass_replace(
            self,
            status=VoucherStatus.PARTIAL,
            updated_at=datetime.now(timezone.utc),
        )

    def mark_settled(self) -> APVoucherAggregate:
        return dataclass_replace(
            self,
            status=VoucherStatus.SETTLED,
            updated_at=datetime.now(timezone.utc),
        )

    def mark_overdue(self, days: int) -> APVoucherAggregate:
        return dataclass_replace(
            self,
            is_overdue=True,
            overdue_days=days,
            updated_at=datetime.now(timezone.utc),
        )

    def red_voucher(self) -> APVoucherAggregate:
        return dataclass_replace(
            self,
            status=VoucherStatus.RED,
            updated_at=datetime.now(timezone.utc),
        )