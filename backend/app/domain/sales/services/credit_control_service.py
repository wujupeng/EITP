"""SAL CreditControlService 领域服务 - 信用控制，含并发安全占用/释放。"""

from __future__ import annotations

from app.domain.sales.aggregates.credit_limit_aggregate import CreditLimitAggregate
from app.domain.sales.value_objects.credit_pricing_vo import (
    CreditCheckResult,
    OverCreditStrategy,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


class CreditControlService:
    """信用控制领域服务。

    输入：(customer_id, 订单金额, 操作类型 check|occupy|release)
    输出：CreditCheckResult
    核心逻辑：查询已用额度（SELECT FOR UPDATE 悲观锁或乐观锁版本号）
            + 校验已用 + 本次 ≤ 额度
            + 超信用按策略处理（BLOCK/WARN/SPECIAL_APPROVAL）
            + 占用/释放 + 并发安全。
    """

    @staticmethod
    def check(credit_limit: CreditLimitAggregate, amount: float) -> CreditCheckResult:
        return credit_limit.check(amount)

    @staticmethod
    def occupy(credit_limit: CreditLimitAggregate, amount: float) -> CreditCheckResult:
        """占用信用额度 - 并发安全（聚合根内 version 乐观锁）。"""
        if amount <= 0:
            raise SALError(SALErrorCode.CREDIT_CONCURRENT_CONFLICT, "占用金额必须为正数")
        return credit_limit.occupy(amount)

    @staticmethod
    def release(credit_limit: CreditLimitAggregate, amount: float) -> None:
        """释放信用额度 - 并发安全。"""
        if amount <= 0:
            raise SALError(SALErrorCode.CREDIT_CONCURRENT_CONFLICT, "释放金额必须为正数")
        credit_limit.release(amount)

    @staticmethod
    def evaluate(
        credit_limit: CreditLimitAggregate,
        amount: float,
        strategy: OverCreditStrategy | None = None,
    ) -> CreditCheckResult:
        """评估信用额度，不实际占用。"""
        if strategy is not None:
            # 临时覆盖策略用于评估
            original = credit_limit.over_credit_strategy
            credit_limit.over_credit_strategy = strategy
            try:
                result = credit_limit.check(amount)
            finally:
                credit_limit.over_credit_strategy = original
            return result
        return credit_limit.check(amount)