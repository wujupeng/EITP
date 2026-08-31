"""黄金链路 E2E 测试 - C-INV-GOLDEN-01。

14 步端到端验证：
  采购入库100 → Reservation 30 → 销售出库30
  → Ledger变化 → Balance变化 → OnHand=70 → Reserved=0 → Available=70

使用真实 API 调用 + 真实数据库状态校验。
"""

from __future__ import annotations

import pytest

from app.application.e2e.golden_path_e2e_suite import GoldenPathE2ETestSuite


@pytest.mark.asyncio
async def test_golden_path_e2e_14_steps():
    """C-INV-GOLDEN-01: 黄金链路 14 步端到端验证。"""
    suite = GoldenPathE2ETestSuite()
    report = await suite.run()

    assert report.total_steps == 14, f"Expected 14 steps, got {report.total_steps}"
    assert report.all_passed, (
        f"Golden path E2E failed: {report.failed_steps} steps failed. "
        f"Details: {report.to_dict()}"
    )
    assert report.passed_steps == 14
    assert report.failed_steps == 0


@pytest.mark.asyncio
async def test_golden_path_e2e_report_structure():
    """验证 E2E 测试报告结构完整性。"""
    suite = GoldenPathE2ETestSuite()
    report = await suite.run()

    report_dict = report.to_dict()
    assert "total_steps" in report_dict
    assert "passed_steps" in report_dict
    assert "failed_steps" in report_dict
    assert "total_duration_ms" in report_dict
    assert "all_passed" in report_dict
    assert "results" in report_dict
    assert len(report_dict["results"]) == 14

    for result in report_dict["results"]:
        assert "step" in result
        assert "name" in result
        assert "passed" in result
        assert "duration_ms" in result