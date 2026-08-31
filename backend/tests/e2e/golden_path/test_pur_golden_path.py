"""PUR 黄金链路 E2E 测试 - C-PUR-GOLDEN-01。

16 步端到端验证：
  创建供应商 → 审批发布 → 创建采购申请 → 审批 → 转单
  → 采购订单审批发送 → 创建ASN → 收货确认(通过WMS Receiving API)
  → 质检 → 创建结算单 → 对账 → 发票匹配 → 付款申请
"""

from __future__ import annotations

import pytest

from app.application.e2e.pur_golden_path_e2e_suite import PurGoldenPathE2ETestSuite


@pytest.mark.asyncio
async def test_pur_golden_path_e2e_16_steps():
    """C-PUR-GOLDEN-01: PUR 黄金链路 16 步端到端验证。"""
    suite = PurGoldenPathE2ETestSuite()
    report = await suite.run()

    assert report.total_steps == 16, f"Expected 16 steps, got {report.total_steps}"
    assert report.all_passed, (
        f"PUR Golden path E2E failed: {report.failed_steps} steps failed. "
        f"Details: {report.to_dict()}"
    )
    assert report.passed_steps == 16
    assert report.failed_steps == 0


@pytest.mark.asyncio
async def test_pur_golden_path_e2e_report_structure():
    """验证 PUR E2E 测试报告结构完整性。"""
    suite = PurGoldenPathE2ETestSuite()
    report = await suite.run()

    report_dict = report.to_dict()
    assert "total_steps" in report_dict
    assert "passed_steps" in report_dict
    assert "failed_steps" in report_dict
    assert "total_duration_ms" in report_dict
    assert "all_passed" in report_dict
    assert "results" in report_dict
    assert len(report_dict["results"]) == 16

    for result in report_dict["results"]:
        assert "step" in result
        assert "name" in result
        assert "passed" in result
        assert "duration_ms" in result