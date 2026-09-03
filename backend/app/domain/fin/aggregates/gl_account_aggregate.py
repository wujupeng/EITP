"""FIN 总账科目聚合根 - GLAccountAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.fin.value_objects.enums import BalanceDirection, GLAccountCategory


@dataclass(frozen=True)
class GLAccountAggregate:
    """总账科目聚合根 - 维护期初/期间发生/期末余额。

    期末余额计算：
      DEBIT 方向: closing = opening + period_debit - period_credit
      CREDIT 方向: closing = opening + period_credit - period_debit
    """

    account_id: UUID
    account_code: str
    account_name: str
    category: GLAccountCategory
    balance_direction: BalanceDirection
    parent_code: str | None
    opening_balance: Decimal
    period_debit: Decimal
    period_credit: Decimal
    closing_balance: Decimal
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def _calc_closing(
        direction: BalanceDirection,
        opening: Decimal,
        debit: Decimal,
        credit: Decimal,
    ) -> Decimal:
        if direction == BalanceDirection.DEBIT:
            return opening + debit - credit
        return opening + credit - debit

    @classmethod
    def create(
        cls,
        account_code: str,
        account_name: str,
        category: GLAccountCategory,
        balance_direction: BalanceDirection,
        tenant_id: UUID,
        parent_code: str | None = None,
        opening_balance: Decimal | None = None,
    ) -> GLAccountAggregate:
        opening = opening_balance if opening_balance is not None else Decimal("0")
        closing = cls._calc_closing(balance_direction, opening, Decimal("0"), Decimal("0"))
        return cls(
            account_id=uuid4(),
            account_code=account_code,
            account_name=account_name,
            category=category,
            balance_direction=balance_direction,
            parent_code=parent_code,
            opening_balance=opening,
            period_debit=Decimal("0"),
            period_credit=Decimal("0"),
            closing_balance=closing,
            tenant_id=tenant_id,
        )

    def update_balance(self, debit: Decimal, credit: Decimal) -> GLAccountAggregate:
        new_debit = self.period_debit + debit
        new_credit = self.period_credit + credit
        new_closing = self._calc_closing(
            self.balance_direction, self.opening_balance, new_debit, new_credit
        )
        return dataclass_replace(
            self,
            period_debit=new_debit,
            period_credit=new_credit,
            closing_balance=new_closing,
            updated_at=datetime.now(timezone.utc),
        )

    def close_period(self) -> GLAccountAggregate:
        return dataclass_replace(
            self,
            opening_balance=self.closing_balance,
            period_debit=Decimal("0"),
            period_credit=Decimal("0"),
            updated_at=datetime.now(timezone.utc),
        )