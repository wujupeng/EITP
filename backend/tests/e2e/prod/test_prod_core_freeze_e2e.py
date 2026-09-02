"""PROD E2E 测试 - Core Freeze 全量校验。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest
from app.application.prod.engine.core_freeze_guard import CoreFreezeGuard, CORE_MILESTONES


class TestProdCoreFreezeE2E:
    """Core Freeze 全量校验 + 9 里程碑回归。"""

    @pytest.mark.asyncio
    async def test_all_9_milestones_covered(self):
        guard = CoreFreezeGuard()
        baseline = await guard.capture_baseline()
        milestones_in_baseline = {fp.milestone for fp in baseline.fingerprints}
        for ms in CORE_MILESTONES:
            assert ms in milestones_in_baseline, f"里程碑 {ms} 未覆盖"

    @pytest.mark.asyncio
    async def test_verify_before_and_after(self):
        guard = CoreFreezeGuard()
        await guard.capture_baseline()
        before = await guard.verify_before()
        after = await guard.verify_after()
        assert len(before) == 0
        assert len(after) == 0