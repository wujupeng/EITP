"""RuleExecutor - 规则执行领域服务。

执行顺序：校验规则（全部通过）→ 拦截规则（全部通过或告警放行）→ 业务操作 → 联动规则（异步触发）
"""

from __future__ import annotations

from uuid import UUID

from app.domain.biz_ops.aggregates.business_rule_aggregate import BusinessRuleAggregate
from app.domain.biz_ops.enums.enums import ExecutionResult, RuleAction, RuleType
from app.domain.biz_ops.services.rule_expression_evaluator import RuleExpressionEvaluator, SimpleExpressionEvaluator
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class RuleTriggerRecord:
    """规则触发记录。"""

    def __init__(self, rule_key: str, rule_type: RuleType, result: ExecutionResult, message: str = ""):
        self.rule_key = rule_key
        self.rule_type = rule_type
        self.result = result
        self.message = message


class RuleExecutor:
    """规则执行领域服务 - 按优先级执行校验/拦截/联动规则。"""

    def __init__(self, evaluator: RuleExpressionEvaluator | None = None) -> None:
        self._evaluator = evaluator or SimpleExpressionEvaluator()

    def execute_validation_rules(
        self, rules: list[BusinessRuleAggregate], context: dict
    ) -> list[RuleTriggerRecord]:
        """执行校验规则 - 全部通过才放行，任一失败立即拒绝。"""
        records: list[RuleTriggerRecord] = []
        sorted_rules = sorted([r for r in rules if r.is_active], key=lambda r: r.priority)
        for rule in sorted_rules:
            if rule.rule_type != RuleType.VALIDATION:
                continue
            try:
                passed = self._evaluator.evaluate(rule.expression, context)
                if passed:
                    records.append(RuleTriggerRecord(rule.rule_key, rule.rule_type, ExecutionResult.PASS))
                else:
                    records.append(RuleTriggerRecord(rule.rule_key, rule.rule_type, ExecutionResult.FAIL, "校验失败"))
                    raise BizOpsError(BizOpsErrorCode.RULE_VALIDATION_FAILED, f"规则校验失败: {rule.rule_key}")
            except BizOpsError:
                raise
            except Exception as e:
                records.append(RuleTriggerRecord(rule.rule_key, rule.rule_type, ExecutionResult.FAIL, str(e)))
                raise BizOpsError(BizOpsErrorCode.RULE_VALIDATION_FAILED, f"规则执行异常: {rule.rule_key}: {e}")
        return records

    def execute_interception_rules(
        self, rules: list[BusinessRuleAggregate], context: dict
    ) -> list[RuleTriggerRecord]:
        """执行拦截规则 - reject 拒绝，warn 告警放行。"""
        records: list[RuleTriggerRecord] = []
        sorted_rules = sorted([r for r in rules if r.is_active], key=lambda r: r.priority)
        for rule in sorted_rules:
            if rule.rule_type != RuleType.INTERCEPTION:
                continue
            try:
                passed = self._evaluator.evaluate(rule.expression, context)
                if passed:
                    records.append(RuleTriggerRecord(rule.rule_key, rule.rule_type, ExecutionResult.PASS))
                else:
                    if rule.action == RuleAction.REJECT:
                        records.append(RuleTriggerRecord(rule.rule_key, rule.rule_type, ExecutionResult.FAIL, "拦截拒绝"))
                        raise BizOpsError(BizOpsErrorCode.RULE_VALIDATION_FAILED, f"规则拦截: {rule.rule_key}")
                    else:
                        records.append(RuleTriggerRecord(rule.rule_key, rule.rule_type, ExecutionResult.WARN, "拦截告警"))
            except BizOpsError:
                raise
            except Exception as e:
                records.append(RuleTriggerRecord(rule.rule_key, rule.rule_type, ExecutionResult.WARN, str(e)))
        return records

    def get_linkage_rules(self, rules: list[BusinessRuleAggregate]) -> list[BusinessRuleAggregate]:
        """获取联动规则 - 由调用方异步执行。"""
        return sorted([r for r in rules if r.is_active and r.rule_type == RuleType.LINKAGE], key=lambda r: r.priority)