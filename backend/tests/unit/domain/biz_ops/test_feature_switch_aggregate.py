"""FeatureSwitchAggregate 单元测试 - 父子继承、模块级关闭强制子功能级关闭、不变量校验。"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.feature_switch_aggregate import FeatureSwitchAggregate
from app.domain.biz_ops.enums.enums import FeatureScope
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


TENANT_ID = uuid4()
USER_ID = uuid4()


class TestFeatureSwitchAggregate:
    """功能开关聚合根测试。"""

    def test_module_level_create(self):
        agg = FeatureSwitchAggregate(
            id=EntityId.generate(),
            tenant_id=TENANT_ID,
            feature_key="purchase",
            scope=FeatureScope.MODULE,
            is_enabled=True,
            updated_by=USER_ID,
        )
        assert agg.feature_key == "purchase"
        assert agg.scope == FeatureScope.MODULE
        assert agg.is_enabled is True

    def test_sub_feature_create(self):
        agg = FeatureSwitchAggregate(
            id=EntityId.generate(),
            tenant_id=TENANT_ID,
            feature_key="purchase.order",
            scope=FeatureScope.SUB_FEATURE,
            is_enabled=True,
            parent_feature_key="purchase",
            updated_by=USER_ID,
        )
        assert agg.parent_feature_key == "purchase"

    def test_module_level_disable_forces_sub_feature_false(self):
        parent = FeatureSwitchAggregate(
            id=EntityId.generate(),
            tenant_id=TENANT_ID,
            feature_key="purchase",
            scope=FeatureScope.MODULE,
            is_enabled=False,
            updated_by=USER_ID,
        )
        child = FeatureSwitchAggregate(
            id=EntityId.generate(),
            tenant_id=TENANT_ID,
            feature_key="purchase.order",
            scope=FeatureScope.SUB_FEATURE,
            is_enabled=True,
            parent_feature_key="purchase",
            updated_by=USER_ID,
        )
        effective = child.resolve_effective(parent)
        assert effective is False

    def test_module_level_enable_allows_sub_feature_independent(self):
        parent = FeatureSwitchAggregate(
            id=EntityId.generate(),
            tenant_id=TENANT_ID,
            feature_key="purchase",
            scope=FeatureScope.MODULE,
            is_enabled=True,
            updated_by=USER_ID,
        )
        child = FeatureSwitchAggregate(
            id=EntityId.generate(),
            tenant_id=TENANT_ID,
            feature_key="purchase.order",
            scope=FeatureScope.SUB_FEATURE,
            is_enabled=False,
            parent_feature_key="purchase",
            updated_by=USER_ID,
        )
        assert child.resolve_effective(parent) is False

        child2 = child.toggle(True, USER_ID)
        assert child2.resolve_effective(parent) is True

    def test_toggle_returns_new_instance(self):
        agg = FeatureSwitchAggregate(
            id=EntityId.generate(),
            tenant_id=TENANT_ID,
            feature_key="sales",
            scope=FeatureScope.MODULE,
            is_enabled=True,
            updated_by=USER_ID,
        )
        toggled = agg.toggle(False, USER_ID)
        assert agg.is_enabled is True
        assert toggled.is_enabled is False
        assert agg.id == toggled.id

    def test_module_level_with_dot_raises(self):
        with pytest.raises(BizOpsError) as exc:
            FeatureSwitchAggregate(
                id=EntityId.generate(),
                tenant_id=TENANT_ID,
                feature_key="purchase.order",
                scope=FeatureScope.MODULE,
                is_enabled=True,
                updated_by=USER_ID,
            )
        assert exc.value.code == BizOpsErrorCode.FEATURE_KEY_FORMAT_INVALID

    def test_module_level_with_parent_raises(self):
        with pytest.raises(BizOpsError) as exc:
            FeatureSwitchAggregate(
                id=EntityId.generate(),
                tenant_id=TENANT_ID,
                feature_key="purchase",
                scope=FeatureScope.MODULE,
                is_enabled=True,
                parent_feature_key="biz_ops",
                updated_by=USER_ID,
            )
        assert exc.value.code == BizOpsErrorCode.FEATURE_SCOPE_MISMATCH

    def test_sub_feature_without_dot_raises(self):
        with pytest.raises(BizOpsError) as exc:
            FeatureSwitchAggregate(
                id=EntityId.generate(),
                tenant_id=TENANT_ID,
                feature_key="purchase_order",
                scope=FeatureScope.SUB_FEATURE,
                is_enabled=True,
                updated_by=USER_ID,
            )
        assert exc.value.code == BizOpsErrorCode.FEATURE_KEY_FORMAT_INVALID

    def test_to_feature_flag(self):
        agg = FeatureSwitchAggregate(
            id=EntityId.generate(),
            tenant_id=TENANT_ID,
            feature_key="warehouse",
            scope=FeatureScope.MODULE,
            is_enabled=True,
            updated_by=USER_ID,
        )
        flag = agg.to_feature_flag()
        assert flag.tenant_id == TENANT_ID
        assert flag.feature_key == "warehouse"
        assert flag.is_on() is True
