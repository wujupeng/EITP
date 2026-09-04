"""PriceConfig 值对象 - 价格配置与阶梯价。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TierPrice:
    """阶梯价 - 按数量区间定价。"""
    min_quantity: float
    max_quantity: float
    unit_price: float


@dataclass(frozen=True)
class PriceConfig:
    """价格配置 - 基准价/折扣率/加成率/阶梯价表。"""
    base_price: float = 0.0
    discount_rate: float = 0.0
    markup_rate: float = 0.0
    tier_prices: tuple[TierPrice, ...] = field(default_factory=tuple)

    def calculate(self, quantity: float = 1.0) -> float:
        """计算价格 - 阶梯价优先，否则基准价×(1-折扣率)×(1+加成率)。"""
        for tier in self.tier_prices:
            if tier.min_quantity <= quantity <= tier.max_quantity:
                return tier.unit_price
        return self.base_price * (1 - self.discount_rate) * (1 + self.markup_rate)