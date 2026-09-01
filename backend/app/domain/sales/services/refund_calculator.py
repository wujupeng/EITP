"""SAL RefundCalculator 领域服务 - 退款金额计算。"""

from __future__ import annotations


class RefundCalculator:
    """退款金额计算服务。

    输入：(退货数量, 原销售单价, 折损)
    输出：退款金额 = 退货数量 × 原销售单价 - 折损
    退款记入销售结算冲抵应收。
    """

    @staticmethod
    def calculate(
        return_quantity: float,
        original_unit_price: float,
        depreciation: float = 0.0,
    ) -> float:
        """计算退款金额。"""
        if return_quantity < 0 or original_unit_price < 0 or depreciation < 0:
            return 0.0
        refund = round(return_quantity * original_unit_price - depreciation, 2)
        return max(refund, 0.0)

    @staticmethod
    def calculate_for_lines(lines: list) -> float:
        """计算多行退款总额。"""
        total = 0.0
        for line in lines:
            if hasattr(line, "refund_amount"):
                total += line.refund_amount
        return round(total, 2)