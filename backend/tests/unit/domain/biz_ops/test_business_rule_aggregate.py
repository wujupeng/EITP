"""BusinessRuleAggregate 单元测试 - 三类规则、版本化、启停、语法校验。"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.business_rule_aggregate import BusinessRuleAggregate
from app.domain.biz_ops.enums.enums import RuleAction, RuleType, ScopeLevel
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


TENANT_ID = uuid4()
USER_ID = uuid4()


class TestBusinessRuleAggregate:
    """业务规则聚合根测试。"""

    def test_validation_rule_create(self):
        agg = BusinessRuleAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, rule_key="val_qty",
            rule_name="数量校验", rule_type=RuleType.VALIDATION,
            trigger_point="purchase.order.create", expression="required:quantity",
        )
        assert agg.rule_type == RuleType.VALIDATION
        assert agg.is_active is True

    def test_interception_rule_with_action(self):
        agg = BusinessRuleAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, rule_key="int_neg",
            rule_name="负库存拦截", rule_type=RuleType.INTERCEPTION,
            trigger_point="inventory.outbound", expression="quantity > 0",
            action=RuleAction.REJECT,
        )
        assert agg.action == RuleAction.REJECT

    def test_interception_rule_without_action_raises(self):
        with pytest.raises(BizOpsError) as exc:
            BusinessRuleAggregate(
                id=EntityId.generate(), tenant_id=TENANT_ID, rule_key="int_neg",
                rule_name="负库存拦截", rule_type=RuleType.INTERCEPTION,
                trigger_point="inventory.outbound", expression="quantity > 0",
            )
        assert exc.value.code == BizOpsErrorCode.RULE_EXPRESSION_INVALID

    def test_linkage_rule_create(self):
        agg = BusinessRuleAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, rule_key="link_qc",
            rule_name="到货质检联动", rule_type=RuleType.LINKAGE,
            trigger_point="purchase.receipt", expression="required:receipt_id",
        )
        assert agg.rule_type == RuleType.LINKAGE

    def test_update_expression_bumps_version(self):
        agg = BusinessRuleAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, rule_key="val_qty",
            rule_name="数量校验", rule_type=RuleType.VALIDATION,
            trigger_point="purchase.order.create", expression="required:quantity",
        )
        updated = agg.update_expression("quantity > 0")
        assert updated.version == 2
        assert agg.version == 1

    def test_activate_deactivate(self):
        agg = BusinessRuleAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, rule_key="val_qty",
            rule_name="数量校验", rule_type=RuleType.VALIDATION,
            trigger_point="purchase.order.create", expression="required:quantity",
        )
        deactivated = agg.deactivate()
        assert deactivated.is_active is False
        activated = deactivated.activate()
        assert activated.is_active is True

    def test_scope_level_requires_scope_ref(self):
        with pytest.raises(BizOpsError):
            BusinessRuleAggregate(
                id=EntityId.generate(), tenant_id=TENANT_ID, rule_key="val_qty",
                rule_name="数量校验", rule_type=RuleType.VALIDATION,
                trigger_point="purchase.order.create", expression="required:quantity",
                scope_level=ScopeLevel.COMPANY,
            )