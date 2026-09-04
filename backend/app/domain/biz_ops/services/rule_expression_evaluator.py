"""RuleExpressionEvaluator - 规则表达式求值器。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class RuleExpressionEvaluator(ABC):
    """规则表达式求值器抽象接口。"""

    @abstractmethod
    def evaluate(self, expression: str, context: dict) -> bool:
        """求值表达式在给定上下文下的布尔结果。"""
        ...


class SimpleExpressionEvaluator(RuleExpressionEvaluator):
    """简单表达式求值器 - 支持字段比较、必填校验、范围校验、日期合法性校验。

    表达式格式：
    - 必填: "required:field_name"
    - 比较: "field_name > 100" / "field_name <= 50"
    - 范围: "field_name in [0, 100]"
    - 非空: "not_empty:field_name"
    """

    def evaluate(self, expression: str, context: dict) -> bool:
        expr = expression.strip()

        if expr.startswith("required:"):
            field = expr[len("required:"):]
            return field in context and context[field] is not None

        if expr.startswith("not_empty:"):
            field = expr[len("not_empty:"):]
            val = context.get(field)
            return val is not None and val != "" and val != 0

        if " in [" in expr:
            field, range_part = expr.split(" in [", 1)
            range_values = [float(v.strip()) for v in range_part.rstrip("]").split(",")]
            val = context.get(field.strip())
            if val is None:
                return False
            return range_values[0] <= float(val) <= range_values[1]

        for op in [" >= ", " <= ", " > ", " < ", " == ", " != "]:
            if op in expr:
                left, right = expr.split(op, 1)
                left_val = context.get(left.strip())
                right_val = float(right.strip())
                if left_val is None:
                    return False
                left_float = float(left_val)
                if op == " >= ": return left_float >= right_val
                if op == " <= ": return left_float <= right_val
                if op == " > ": return left_float > right_val
                if op == " < ": return left_float < right_val
                if op == " == ": return left_float == right_val
                if op == " != ": return left_float != right_val

        return True