"""Money Decimal 高精度金额值对象 - 强制 Decimal 运算，禁止 float。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError


@dataclass(frozen=True)
class Money:
    """金额值对象 - Decimal 高精度，精度两位小数（最小单位到分）。"""

    amount: Decimal
    currency: str = "CNY"

    def __post_init__(self) -> None:
        if isinstance(self.amount, float):
            raise FINError(
                FINErrorCode.MONEY_FLOAT_FORBIDDEN,
                "float type is forbidden for money amount, use Decimal or str",
            )
        if not isinstance(self.amount, Decimal):
            try:
                object.__setattr__(self, "amount", Decimal(str(self.amount)))
            except (InvalidOperation, ValueError) as exc:
                raise FINError(
                    FINErrorCode.MONEY_PRECISION_LOSS,
                    f"cannot convert {self.amount!r} to Decimal: {exc}",
                ) from exc
        if self.amount < 0:
            raise FINError(
                FINErrorCode.MONEY_NEGATIVE_FORBIDDEN,
                f"negative amount is forbidden: {self.amount}",
            )
        quantized = self.amount.quantize(Decimal("0.01"))
        if quantized != self.amount:
            raise FINError(
                FINErrorCode.MONEY_PRECISION_LOSS,
                f"precision exceeds 2 decimal places: {self.amount}",
            )
        object.__setattr__(self, "amount", quantized)

    @classmethod
    def from_str(cls, amount: str, currency: str = "CNY") -> Money:
        return cls(Decimal(amount), currency)

    @classmethod
    def zero(cls, currency: str = "CNY") -> Money:
        return cls(Decimal("0"), currency)

    def add(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: Money) -> Money:
        self._check_currency(other)
        result = self.amount - other.amount
        if result < 0:
            raise FINError(
                FINErrorCode.MONEY_NEGATIVE_FORBIDDEN,
                f"subtraction result is negative: {result}",
            )
        return Money(result, self.currency)

    def multiply(self, factor: Decimal | int) -> Money:
        if isinstance(factor, float):
            raise FINError(
                FINErrorCode.MONEY_FLOAT_FORBIDDEN,
                "float factor is forbidden, use Decimal or int",
            )
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def _check_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise FINError(
                FINErrorCode.MONEY_CURRENCY_MISMATCH,
                f"currency mismatch: {self.currency} vs {other.currency}",
            )

    @staticmethod
    def is_conserved(receivable: Money, received: Money, unreceived: Money) -> bool:
        """校验应收 = 已收 + 未收守恒。"""
        return receivable.amount == received.amount + unreceived.amount

    @staticmethod
    def is_ap_conserved(payable: Money, paid: Money, unpaid: Money) -> bool:
        """校验应付 = 已付 + 未付守恒。"""
        return payable.amount == paid.amount + unpaid.amount

    def __add__(self, other: Money) -> Money:
        return self.add(other)

    def __sub__(self, other: Money) -> Money:
        return self.subtract(other)

    def __mul__(self, factor: Decimal | int) -> Money:
        return self.multiply(factor)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount >= other.amount

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"