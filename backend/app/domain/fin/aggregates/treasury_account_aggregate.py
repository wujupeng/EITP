"""FIN 资金账户聚合根 - TreasuryAccountAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import TreasuryAccountType
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class TreasuryAccountAggregate:
    """资金账户聚合根 - 余额/冻结/可用余额守恒。"""

    account_id: UUID
    account_no: str
    account_type: TreasuryAccountType
    currency: str
    balance: Money
    frozen_amount: Money
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        account_no: str,
        account_type: TreasuryAccountType,
        currency: str,
        opening_balance: Money,
        tenant_id: UUID,
    ) -> TreasuryAccountAggregate:
        return cls(
            account_id=uuid4(),
            account_no=account_no,
            account_type=account_type,
            currency=currency,
            balance=opening_balance,
            frozen_amount=Money.zero(currency),
            tenant_id=tenant_id,
        )

    def available_balance(self) -> Money:
        return self.balance.subtract(self.frozen_amount)

    def freeze(self, amount: Money) -> TreasuryAccountAggregate:
        new_frozen = self.frozen_amount.add(amount)
        if new_frozen > self.balance:
            raise FINError(
                FINErrorCode.TREASURY_FREEZE_EXCEED,
                f"freeze {amount} exceeds available balance "
                f"{self.available_balance()} for account {self.account_no}",
            )
        return dataclass_replace(
            self,
            frozen_amount=new_frozen,
            updated_at=datetime.now(timezone.utc),
        )

    def unfreeze(self, amount: Money) -> TreasuryAccountAggregate:
        if amount > self.frozen_amount:
            raise FINError(
                FINErrorCode.TREASURY_FREEZE_EXCEED,
                f"unfreeze {amount} exceeds frozen {self.frozen_amount} "
                f"for account {self.account_no}",
            )
        new_frozen = self.frozen_amount.subtract(amount)
        return dataclass_replace(
            self,
            frozen_amount=new_frozen,
            updated_at=datetime.now(timezone.utc),
        )

    def deposit(self, amount: Money) -> TreasuryAccountAggregate:
        new_balance = self.balance.add(amount)
        return dataclass_replace(
            self,
            balance=new_balance,
            updated_at=datetime.now(timezone.utc),
        )

    def withdraw(self, amount: Money) -> TreasuryAccountAggregate:
        if amount > self.available_balance():
            raise FINError(
                FINErrorCode.TREASURY_INSUFFICIENT_BALANCE,
                f"withdraw {amount} exceeds available {self.available_balance()} "
                f"for account {self.account_no}",
            )
        new_balance = self.balance.subtract(amount)
        return dataclass_replace(
            self,
            balance=new_balance,
            updated_at=datetime.now(timezone.utc),
        )