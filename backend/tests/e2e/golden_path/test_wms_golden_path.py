"""WMS 黄金链路 E2E 测试 - 10 步端到端验证。

C-WMS-GOLDEN-01: 采购到货100 → 收货 → QC → 上架 → 拣货30 → 发货30
  → WMS Position = 70 ↔ INV OnHand = 70 → Ledger 5 条 → 全程 WMS 通过 INV API

使用真实 API 调用 + 真实数据库状态校验。
需要完整数据库环境。
"""

from __future__ import annotations

import pytest

from app.application.e2e.wms_golden_path_e2e_suite import WmsGoldenPathE2ETestSuite


@pytest.fixture(scope="module")
async def e2e_report():
    """共享 E2E 套件运行结果，避免重复执行导致的连接池问题。"""
    suite = WmsGoldenPathE2ETestSuite()
    report = await suite.run()
    return report


@pytest.mark.asyncio
async def test_wms_golden_path_10_steps(e2e_report):
    """C-WMS-GOLDEN-01: WMS 黄金链路 10 步端到端验证。"""
    report = e2e_report
    assert report.total_steps == 10, f"Expected 10 steps, got {report.total_steps}"
    assert report.all_passed, (
        f"WMS golden path E2E failed: {report.failed_steps} steps failed. "
        f"Details: {report.to_dict()}"
    )
    assert report.passed_steps == 10
    assert report.failed_steps == 0


@pytest.mark.asyncio
async def test_wms_golden_path_report_structure(e2e_report):
    """验证 WMS E2E 测试报告结构完整性。"""
    report = e2e_report
    report_dict = report.to_dict()
    assert "total_steps" in report_dict
    assert "passed_steps" in report_dict
    assert "failed_steps" in report_dict
    assert "total_duration_ms" in report_dict
    assert "all_passed" in report_dict
    assert "results" in report_dict
    assert len(report_dict["results"]) == 10

    for result in report_dict["results"]:
        assert "step" in result
        assert "name" in result
        assert "passed" in result
        assert "duration_ms" in result


@pytest.mark.asyncio
async def test_wms_golden_path_final_consistency(e2e_report):
    """验证最终一致性：WMS Position = 70 ↔ INV OnHand = 70。"""
    report = e2e_report
    if report.all_passed:
        last_step = report.results[-1]
        assert last_step.passed, "Final consistency step should pass"
        assert last_step.actual.get("wms_qty") == 70.0, f"WMS qty={last_step.actual.get('wms_qty')}"
        assert last_step.actual.get("inv_on_hand") == 70.0, f"INV on_hand={last_step.actual.get('inv_on_hand')}"
    else:
        pytest.skip(f"Golden path failed before final consistency: {report.to_dict()}")
