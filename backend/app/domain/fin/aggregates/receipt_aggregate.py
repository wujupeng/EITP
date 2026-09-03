"""FIN 收款聚合根 - ReceiptAggregate + WriteOffLine。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import ReceiptStatus
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class WriteOffLine:
    """核销明细行 - 关联 AR 凭证与核销金额。"""

    line_no: int
    ar_voucher_no: str
    write_off_amount: Money


@dataclass(frozen=True)
class ReceiptAggregate:
    """收款聚合根 - 状态机 + 核销金额守恒。"""

    receipt_id: UUID
    receipt_no: str
    receipt_amount: Money
    receiver_account: str
    payer_account: str
    bank_ref: str | None
    status: ReceiptStatus
    write_off_lines: tuple[WriteOffLine, ...]
    arrival_time: datetime | None
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        receipt_no: str,
        receipt_amount: Money,
        receiver_account: str,
        payer_account: str,
        tenant_id: UUID,
        bank_ref: str | None = None,
        arrival_time: datetime | None = None,
    ) -> ReceiptAggregate:
        return cls(
            receipt_id=uuid4(),
            receipt_no=receipt_no,
            receipt_amount=receipt_amount,
            receiver_account=receiver_account,
            payer_account=payer_account,
            bank_ref=bank_ref,
            status=ReceiptStatus.PENDING_CONFIRM,
            write_off_lines=(),
            arrival_time=arrival_time,
            tenant_id=tenant_id,
        )

    def _check_transition(self, expected: ReceiptStatus) -> None:
        if self.status != expected:
            raise FINError(
                FINErrorCode.RECEIPT_INVALID_TRANSITION,
                f"receipt {self.receipt_no} invalid transition: "
                f"{self.status.value} -> expected {expected.value}",
            )

    def _total_write_off(self) -> Money:
        if not self.write_off_lines:
            return Money.zero(self.receipt_amount.currency)
        total = self.write_off_lines[0].write_off_amount
        for ln in self.write_off_lines[1:]:
            total = total.add(ln.write_off_amount)
        return total

    def confirm(self) -> ReceiptAggregate:
        self._check_transition(ReceiptStatus.PENDING_CONFIRM)
        return dataclass_replace(
            self,
            status=ReceiptStatus.CONFIRMED,
            updated_at=datetime.now(timezone.utc),
        )

    def write_off(self, lines: list[WriteOffLine]) -> ReceiptAggregate:
        self._check_transition(ReceiptStatus.CONFIRMED)
        line_tuple = tuple(lines)
        total = line_tuple[0].write_off_amount
        for ln in line_tuple[1:]:
            total = total.add(ln.write_off_amount)
        if total > self.receipt_amount:
            raise FINError(
                FINErrorCode.RECEIPT_WRITEOFF_EXCEED,
                f"write-off total {total} exceeds receipt amount {self.receipt_amount}",
            )
        return dataclass_replace(
            self,
            status=ReceiptStatus.WRITE_OFF,
            write_off_lines=line_tuple,
            updated_at=datetime.now(timezone.utc),
        )

    def cancel(self) -> ReceiptAggregate:
        if self.status not in (
            ReceiptStatus.PENDING_CONFIRM,
            ReceiptStatus.CONFIRMED,
        ):
            raise FINError(
                FINErrorCode.RECEIPT_INVALID_TRANSITION,
                f"receipt {self.receipt_no} cannot cancel from {self.status.value}",
            )
        return dataclass_replace(
            self,
            status=ReceiptStatus.CANCELLED,
            updated_at=datetime.now(timezone.utc),
        )

    def remaining_amount(self) -> Money:
        return self.receipt_amount.subtract(self._total_write_off())