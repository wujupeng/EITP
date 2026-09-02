"""PROD 集成测试 - Core Freeze 守卫。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest
from app.application.prod.engine.core_freeze_guard import CoreFreezeGuard


class TestProdCoreFreezeEnforcement:
    """Core Freeze 守卫 + 核心变更检测。"""

    @pytest.mark.asyncio
    async def test_baseline_capture(self):
        guard = CoreFreezeGuard()
        baseline = await guard.capture_baseline()
        assert len(baseline.fingerprints) > 0

    @pytest.mark.asyncio
    async def test_verify_before_no_violations(self):
        guard = CoreFreezeGuard()
        await guard.capture_baseline()
        violations = await guard.verify_before()
        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_verify_after_no_violations(self):
        guard = CoreFreezeGuard()
        await guard.capture_baseline()
        violations = await guard.verify_after()
        assert len(violations) == 0

    def test_violations_to_detail_format(self):
        from app.application.prod.engine.core_freeze_guard import FreezeViolation
        violations = [FreezeViolation("MT", "model", "app.domain.mt", "abc", "def")]
        detail = CoreFreezeGuard.violations_to_detail(violations)
        assert detail["violation_count"] == 1