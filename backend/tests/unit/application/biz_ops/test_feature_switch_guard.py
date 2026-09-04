"""FeatureSwitchGuard 单元测试 - 缓存命中、降级策略、功能开关校验。"""

from __future__ import annotations

import os
import sys
import time
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.application.biz_ops.feature_switch_guard import FeatureSwitchGuard


TENANT_ID = uuid4()


class TestFeatureSwitchGuard:
    """功能开关守卫测试。"""

    def test_cache_invalidation(self):
        FeatureSwitchGuard._cache[f"{TENANT_ID}:test_key"] = (True, time.monotonic())
        assert len(FeatureSwitchGuard._cache) > 0
        FeatureSwitchGuard.invalidate_cache(TENANT_ID)
        assert len(FeatureSwitchGuard._cache) == 0

    def test_cache_invalidation_all(self):
        FeatureSwitchGuard._cache["key1"] = (True, time.monotonic())
        FeatureSwitchGuard._cache["key2"] = (False, time.monotonic())
        FeatureSwitchGuard.invalidate_cache()
        assert len(FeatureSwitchGuard._cache) == 0

    def test_degrade_strategy_allow(self):
        guard = FeatureSwitchGuard(degrade_strategy="allow")
        assert guard._degrade_strategy == "allow"

    def test_degrade_strategy_deny(self):
        guard = FeatureSwitchGuard(degrade_strategy="deny")
        assert guard._degrade_strategy == "deny"