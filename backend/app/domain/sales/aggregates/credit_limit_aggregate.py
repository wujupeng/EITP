"""SAL CreditLimitAggregate 聚合根 - 信用额度，含并发安全占用/释放。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.value_objects.credit_pricing_vo import (
    CreditCheckResult,
    OverCreditStrategy,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


@dataclass
class CreditLimitAggregate:
    """信用额度聚合根 - 禁止贫血模型。

    不变量：used_amount ≥ 0，available_amount = total_limit - used_amount。
    复合唯一约束：(tenant_id, customer_id)。
    """

    credit_limit_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    customer_id: UUID = field(default_factory=uuid4)
    total_limit: float = 0.0
    used_amount: float = 0.0
    credit_period_days: int = 30
    over_credit_strategy: OverCreditStrategy = OverCreditStrategy.BLOCK
    version: int = 1  # 乐观锁版本号
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.total_limit <= 0:
            raise SALError(SALErrorCode.CREDIT_CONFIG_NOT_FOUND, "信用总额度必须为正数")
        if self.used_amount < 0:
            raise SALError(SALErrorCode.CREDIT_CONCURRENT_CONFLICT, "已用额度不可为负")

    @property
    def available_amount(self) -> float:
        """可用额度 = 总额度 - 已用额度。"""
        return round(self.total_limit - self.used_amount, 2)

    def check(self, amount: float) -> CreditCheckResult:
        """校验已用 + 本次 ≤ 额度，返回 CreditCheckResult。"""
        if amount < 0:
            raise SALError(SALErrorCode.CREDIT_CONCURRENT_CONFLICT, "校验金额不可为负")
        after_used = round(self.used_amount + amount, 2)
        is_over = after_used > self.total_limit
        if not is_over:
            result = "pass"
        elif self.over_credit_strategy == OverCreditStrategy.BLOCK:
            result = "block"
        elif self.over_credit_strategy == OverCreditStrategy.WARN:
            result = "warn"
        else:
            result = "special_approval"
        return CreditCheckResult(
            before_used=self.used_amount,
            this_amount=amount,
            after_used=after_used,
            is_over_credit=is_over,
            strategy=self.over_credit_strategy,
            result=result,  # type: ignore[arg-type]
        )

    def occupy(self, amount: float) -> CreditCheckResult:
        """占用额度：已用 += amount，超信用按策略处理。"""
        result = self.check(amount)
        if result.result == "block":
            raise SALError(
                SALErrorCode.CREDIT_LIMIT_EXCEEDED,
                f"信用额度超限: 已用 {self.used_amount} + 本次 {amount}"
                f" > 总额度 {self.total_limit}",
            )
        self.used_amount = round(self.used_amount + amount, 2)
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
        return result

    def release(self, amount: float) -> None:
        """释放额度：已用 -= amount，不可低于 0。"""
        if amount < 0:
            raise SALError(SALErrorCode.CREDIT_CONCURRENT_CONFLICT, "释放金额不可为负")
        if amount > self.used_amount:
            raise SALError(
                SALErrorCode.CREDIT_CONCURRENT_CONFLICT,
                f"释放金额超过已用额度: 释放 {amount} > 已用 {self.used_amount}",
            )
        self.used_amount = round(self.used_amount - amount, 2)
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)