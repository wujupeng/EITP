"""FIN 应收凭证聚合根 - ARVoucherAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import VoucherStatus
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class ARVoucherAggregate:
    """应收凭证聚合根 - 金额守恒 receivable = received + unreceived。"""

    voucher_id: UUID
    voucher_no: str
    business_ref_type: str
    business_ref_id: str
    receivable_amount: Money
    received_amount: Money
    unreceived_amount: Money
    status: VoucherStatus
    credit_period_days: int
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
        receivable_amount: Money,
        tenant_id: UUID,
        credit_period_days: int = 30,
        due_date: date | None = None,
    ) -> ARVoucherAggregate:
        return cls(
            voucher_id=uuid4(),
            voucher_no=voucher_no,
            business_ref_type=business_ref_type,
            business_ref_id=business_ref_id,
            receivable_amount=receivable_amount,
            received_amount=Money.zero(receivable_amount.currency),
            unreceived_amount=receivable_amount,
            status=VoucherStatus.OPEN,
            credit_period_days=credit_period_days,
            due_date=due_date,
            is_overdue=False,
            overdue_days=0,
            tenant_id=tenant_id,
        )

    def _check_balance(self) -> None:
        if not Money.is_conserved(
            self.receivable_amount, self.received_amount, self.unreceived_amount
        ):
            raise FINError(
                FINErrorCode.AR_UNBALANCED,
                f"AR voucher {self.voucher_no} unbalanced: "
                f"receivable={self.receivable_amount} != "
                f"received={self.received_amount} + unreceived={self.unreceived_amount}",
            )

    def apply_receipt(self, amount: Money) -> ARVoucherAggregate:
        if amount > self.unreceived_amount:
            raise FINError(
                FINErrorCode.RECEIPT_WRITEOFF_EXCEED,
                f"receipt amount {amount} exceeds unreceived {self.unreceived_amount}",
            )
        new_received = self.received_amount.add(amount)
        new_unreceived = self.unreceived_amount.subtract(amount)
        if not Money.is_conserved(
            self.receivable_amount, new_received, new_unreceived
        ):
            raise FINError(
                FINErrorCode.AR_UNBALANCED,
                f"AR voucher {self.voucher_no} unbalanced after receipt",
            )
        zero = Money.zero(self.receivable_amount.currency)
        if new_received == self.receivable_amount:
            status = VoucherStatus.SETTLED
        elif new_received > zero:
            status = VoucherStatus.PARTIAL
        else:
            status = VoucherStatus.OPEN
        return dataclass_replace(
            self,
            received_amount=new_received,
            unreceived_amount=new_unreceived,
            status=status,
            updated_at=datetime.now(timezone.utc),
        )

    def mark_partial(self) -> ARVoucherAggregate:
        return dataclass_replace(
            self,
            status=VoucherStatus.PARTIAL,
            updated_at=datetime.now(timezone.utc),
        )

    def mark_settled(self) -> ARVoucherAggregate:
        return dataclass_replace(
            self,
            status=VoucherStatus.SETTLED,
            updated_at=datetime.now(timezone.utc),
        )

    def mark_overdue(self, days: int) -> ARVoucherAggregate:
        return dataclass_replace(
            self,
            is_overdue=True,
            overdue_days=days,
            updated_at=datetime.now(timezone.utc),
        )

    def red_voucher(self) -> ARVoucherAggregate:
        return dataclass_replace(
            self,
            status=VoucherStatus.RED,
            updated_at=datetime.now(timezone.utc),
        )