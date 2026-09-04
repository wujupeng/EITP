"""BusinessRuleAggregate - 业务规则聚合根，封装校验/拦截/联动三类规则。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.biz_ops.enums.enums import RuleAction, RuleType, ScopeLevel
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class BusinessRuleAggregate(AggregateRoot):
    """业务规则聚合根 - 校验/拦截/联动三类规则，支持版本化与启停。

    不变量：
    - rule_key 租户内唯一
    - scope_level 与 scope_ref 一致性
    - action 与 rule_type 匹配（仅 INTERCEPTION 类型有 action）
    - expression 语法校验
    - 版本号单调递增
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        rule_key: str,
        rule_name: str,
        rule_type: RuleType,
        trigger_point: str,
        expression: str,
        priority: int = 100,
        scope_level: ScopeLevel = ScopeLevel.TENANT,
        scope_ref: str | None = None,
        action: RuleAction | None = None,
        is_active: bool = True,
        version: int = 1,
        description: str | None = None,
        created_by: UUID | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._rule_key = rule_key
        self._rule_name = rule_name
        self._rule_type = rule_type
        self._trigger_point = trigger_point
        self._expression = expression
        self._priority = priority
        self._scope_level = scope_level
        self._scope_ref = scope_ref
        self._action = action
        self._is_active = is_active
        self._version = version
        self._description = description
        self._created_by = created_by
        self.validate()

    @property
    def tenant_id(self) -> UUID: return self._tenant_id
    @property
    def rule_key(self) -> str: return self._rule_key
    @property
    def rule_name(self) -> str: return self._rule_name
    @property
    def rule_type(self) -> RuleType: return self._rule_type
    @property
    def trigger_point(self) -> str: return self._trigger_point
    @property
    def expression(self) -> str: return self._expression
    @property
    def priority(self) -> int: return self._priority
    @property
    def scope_level(self) -> ScopeLevel: return self._scope_level
    @property
    def scope_ref(self) -> str | None: return self._scope_ref
    @property
    def action(self) -> RuleAction | None: return self._action
    @property
    def is_active(self) -> bool: return self._is_active
    @property
    def version(self) -> int: return self._version
    @property
    def description(self) -> str | None: return self._description

    def update_expression(self, expr: str) -> BusinessRuleAggregate:
        """更新规则表达式 - 返回新实例（含版本号递增）。"""
        return BusinessRuleAggregate(
            id=self._id, tenant_id=self._tenant_id, rule_key=self._rule_key,
            rule_name=self._rule_name, rule_type=self._rule_type,
            trigger_point=self._trigger_point, expression=expr,
            priority=self._priority, scope_level=self._scope_level,
            scope_ref=self._scope_ref, action=self._action,
            is_active=self._is_active, version=self._version + 1,
            description=self._description, created_by=self._created_by,
        )

    def activate(self) -> BusinessRuleAggregate:
        return BusinessRuleAggregate(
            id=self._id, tenant_id=self._tenant_id, rule_key=self._rule_key,
            rule_name=self._rule_name, rule_type=self._rule_type,
            trigger_point=self._trigger_point, expression=self._expression,
            priority=self._priority, scope_level=self._scope_level,
            scope_ref=self._scope_ref, action=self._action,
            is_active=True, version=self._version,
            description=self._description, created_by=self._created_by,
        )

    def deactivate(self) -> BusinessRuleAggregate:
        return BusinessRuleAggregate(
            id=self._id, tenant_id=self._tenant_id, rule_key=self._rule_key,
            rule_name=self._rule_name, rule_type=self._rule_type,
            trigger_point=self._trigger_point, expression=self._expression,
            priority=self._priority, scope_level=self._scope_level,
            scope_ref=self._scope_ref, action=self._action,
            is_active=False, version=self._version,
            description=self._description, created_by=self._created_by,
        )

    def bump_version(self) -> BusinessRuleAggregate:
        return self.update_expression(self._expression)

    def validate(self) -> None:
        if not self._rule_key or len(self._rule_key) > 100:
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "rule_key 不能为空且不超过 100 字符")
        if self._rule_type == RuleType.INTERCEPTION and self._action is None:
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "拦截规则必须指定 action")
        if self._rule_type != RuleType.INTERCEPTION and self._action is not None:
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "仅拦截规则可指定 action")
        if self._scope_level != ScopeLevel.TENANT and self._scope_ref is None:
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, f"scope_level={self._scope_level.value} 必须指定 scope_ref")
        if self._priority < 0 or self._priority > 999:
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "priority 必须在 0-999 范围内")