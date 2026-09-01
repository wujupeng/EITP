"""AggregateDataReversibilityChecker 领域服务 - 检测聚合数据是否可逆向推导明细。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.interfaces.middleware.error_handler import SECError, SECErrorCode


@dataclass
class ReversibilityAssessment:
    is_reversible: bool
    risk_detail: str
    recommendation: str = ""


class AggregateDataReversibilityChecker:
    """分析聚合粒度，检测是否可逆向推导明细。"""

    _SINGLE_RECORD_THRESHOLD = 1
    _LOW_COUNT_THRESHOLD = 3

    def check(
        self,
        aggregate_result: dict[str, Any],
        aggregate_count: int,
        known_context: dict[str, Any] | None = None,
    ) -> ReversibilityAssessment:
        if aggregate_count <= self._SINGLE_RECORD_THRESHOLD:
            return ReversibilityAssessment(
                is_reversible=True,
                risk_detail=f"Aggregate count={aggregate_count}, single record can be fully inferred",
                recommendation="Increase aggregation granularity or add noise (k-anonymity, k>=3)",
            )

        if aggregate_count <= self._LOW_COUNT_THRESHOLD:
            return ReversibilityAssessment(
                is_reversible=True,
                risk_detail=f"Aggregate count={aggregate_count}, low count allows partial inference",
                recommendation="Increase aggregation granularity to k>=5 or suppress small counts",
            )

        if self._check_zero_variance(aggregate_result):
            return ReversibilityAssessment(
                is_reversible=True,
                risk_detail="All values identical, individual values fully exposed",
                recommendation="Add noise or coarsen the aggregation dimension",
            )

        if known_context and self._check_context_overlap(aggregate_result, known_context):
            return ReversibilityAssessment(
                is_reversible=True,
                risk_detail="Known context overlaps with aggregate, individual inference possible",
                recommendation="Remove overlapping dimensions from external context",
            )

        return ReversibilityAssessment(
            is_reversible=False,
            risk_detail=f"Aggregate count={aggregate_count}, sufficient anonymity",
        )

    @staticmethod
    def _check_zero_variance(result: dict[str, Any]) -> bool:
        values: list[float] = []
        for v in result.values():
            if isinstance(v, int | float):
                values.append(float(v))
        if len(values) < 2:
            return False
        return max(values) == min(values)

    @staticmethod
    def _check_context_overlap(result: dict[str, Any], context: dict[str, Any]) -> bool:
        shared_keys = set(result.keys()) & set(context.keys())
        return len(shared_keys) >= 2

    def assert_non_reversible(self, aggregate_result: dict[str, Any], aggregate_count: int) -> None:
        assessment = self.check(aggregate_result, aggregate_count)
        if assessment.is_reversible:
            raise SECError(SECErrorCode.AGGREGATE_REVERSIBLE, assessment.risk_detail)