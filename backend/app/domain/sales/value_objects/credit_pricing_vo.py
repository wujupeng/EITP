"""SAL 信用与价格值对象 - OverCreditStrategy/CreditCheckResult/PriceType 等。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class OverCreditStrategy(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    SPECIAL_APPROVAL = "special_approval"


class PriceType(str, Enum):
    AGREEMENT = "agreement"
    DISCOUNT = "discount"
    PROMOTION = "promotion"
    STANDARD = "standard"


@dataclass(frozen=True)
class PricePriority:
    """价格优先级值对象：促销 1 > 协议 2 > 折扣 3 > 标准 4。"""

    value: int

    @classmethod
    def from_price_type(cls, price_type: PriceType) -> PricePriority:
        return cls({
            PriceType.PROMOTION: 1,
            PriceType.AGREEMENT: 2,
            PriceType.DISCOUNT: 3,
            PriceType.STANDARD: 4,
        }[price_type])

    def __lt__(self, other: PricePriority) -> bool:
        return self.value < other.value

    def __le__(self, other: PricePriority) -> bool:
        return self.value <= other.value


@dataclass(frozen=True)
class CreditCheckResult:
    """信用校验结果值对象。"""

    before_used: float
    this_amount: float
    after_used: float
    is_over_credit: bool
    strategy: OverCreditStrategy
    result: Literal["pass", "block", "warn", "special_approval"]

    @property
    def is_pass(self) -> bool:
        return self.result == "pass"


@dataclass(frozen=True)
class PricingMatchResult:
    """价格匹配结果值对象。"""

    matched_price_type: PriceType
    final_unit_price: float
    priority: PricePriority
    matched_pricing_id: UUID | None = None  # noqa: F821

    @classmethod
    def standard(cls, unit_price: float) -> PricingMatchResult:
        return cls(
            matched_price_type=PriceType.STANDARD,
            final_unit_price=unit_price,
            priority=PricePriority(4),
            matched_pricing_id=None,
        )