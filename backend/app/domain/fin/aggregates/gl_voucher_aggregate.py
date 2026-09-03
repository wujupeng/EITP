"""FIN 总账凭证聚合根 - GLVoucherAggregate + GLVoucherLine。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class GLVoucherLine:
    """总账凭证行 - 单行借贷金额，金额使用 Money 非负。"""

    line_no: int
    account_code: str
    debit_amount: Money
    credit_amount: Money


@dataclass(frozen=True)
class GLVoucherAggregate:
    """总账凭证聚合根 - 借贷平衡 + 期间锁定 + 红冲。"""

    gl_voucher_id: UUID
    voucher_no: str
    voucher_date: date
    summary: str
    business_ref_type: str | None
    business_ref_id: str | None
    red_original_voucher_no: str | None
    period: str
    is_period_closed: bool
    lines: tuple[GLVoucherLine, ...]
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        voucher_no: str,
        voucher_date: date,
        summary: str,
        period: str,
        tenant_id: UUID,
        lines: list[GLVoucherLine] | tuple[GLVoucherLine, ...],
        business_ref_type: str | None = None,
        business_ref_id: str | None = None,
    ) -> GLVoucherAggregate:
        return cls(
            gl_voucher_id=uuid4(),
            voucher_no=voucher_no,
            voucher_date=voucher_date,
            summary=summary,
            business_ref_type=business_ref_type,
            business_ref_id=business_ref_id,
            red_original_voucher_no=None,
            period=period,
            is_period_closed=False,
            lines=tuple(lines),
            tenant_id=tenant_id,
        )

    def _check_period_open(self) -> None:
        if self.is_period_closed:
            raise FINError(
                FINErrorCode.GL_PERIOD_CLOSED,
                f"period {self.period} already closed, voucher {self.voucher_no} immutable",
            )

    def _total_debit(self) -> Money:
        if not self.lines:
            return Money.zero()
        total = self.lines[0].debit_amount
        for line in self.lines[1:]:
            total = total.add(line.debit_amount)
        return total

    def _total_credit(self) -> Money:
        if not self.lines:
            return Money.zero()
        total = self.lines[0].credit_amount
        for line in self.lines[1:]:
            total = total.add(line.credit_amount)
        return total

    def is_balanced(self) -> bool:
        return self._total_debit() == self._total_credit()

    def post(self) -> GLVoucherAggregate:
        self._check_period_open()
        total_debit = self._total_debit()
        total_credit = self._total_credit()
        if total_debit != total_credit:
            raise FINError(
                FINErrorCode.GL_UNBALANCED,
                f"GL voucher {self.voucher_no} unbalanced: "
                f"debit={total_debit} != credit={total_credit}",
            )
        return dataclass_replace(self, updated_at=datetime.now(timezone.utc))

    def red_voucher(self, new_voucher_no: str) -> GLVoucherAggregate:
        self._check_period_open()
        red_lines = tuple(
            GLVoucherLine(
                line_no=line.line_no,
                account_code=line.account_code,
                debit_amount=line.credit_amount,
                credit_amount=line.debit_amount,
            )
            for line in self.lines
        )
        now = datetime.now(timezone.utc)
        return GLVoucherAggregate(
            gl_voucher_id=uuid4(),
            voucher_no=new_voucher_no,
            voucher_date=self.voucher_date,
            summary=f"RED: {self.summary}",
            business_ref_type=self.business_ref_type,
            business_ref_id=self.business_ref_id,
            red_original_voucher_no=self.voucher_no,
            period=self.period,
            is_period_closed=False,
            lines=red_lines,
            tenant_id=self.tenant_id,
            created_at=now,
            updated_at=now,
        )

    def close_period(self) -> GLVoucherAggregate:
        self._check_period_open()
        return dataclass_replace(
            self,
            is_period_closed=True,
            updated_at=datetime.now(timezone.utc),
        )