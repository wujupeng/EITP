"""SAL 对账与发票匹配校验领域服务。"""

from __future__ import annotations

from app.interfaces.middleware.error_handler import SALError, SALErrorCode


class ReconcileDiffChecker:
    """对账差异校验服务 - 超阈值拒绝。

    配置：sal.reconcile_diff_threshold，默认 0.01。
    """

    def __init__(self, threshold: float = 0.01) -> None:
        self.threshold = threshold

    def check(self, expected: float, actual: float) -> float:
        """校验差异，返回差异值，超阈值抛异常。"""
        diff = round(actual - expected, 2)
        if abs(diff) > self.threshold:
            raise SALError(
                SALErrorCode.SETTLEMENT_RECONCILE_DIFF_EXCEEDED,
                f"对账差异超阈值: |{actual} - {expected}| = {abs(diff)} > {self.threshold}",
            )
        return diff


class InvoiceMatchChecker:
    """发票匹配校验服务 - 超阈值拒绝。

    配置：sal.invoice_match_diff_threshold，默认 0.01。
    """

    def __init__(self, threshold: float = 0.01) -> None:
        self.threshold = threshold

    def check(self, invoice_amount: float, expected_amount: float) -> float:
        """校验发票匹配差异，返回差异值，超阈值抛异常。"""
        diff = round(invoice_amount - expected_amount, 2)
        if abs(diff) > self.threshold:
            raise SALError(
                SALErrorCode.INVOICE_MATCH_DIFF_EXCEEDED,
                f"发票匹配差异超阈值: |{invoice_amount} - {expected_amount}|"
                f" = {abs(diff)} > {self.threshold}",
            )
        return diff