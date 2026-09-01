"""SAL 黄金链路 E2E 测试 - C-SAL-GOLDEN-01。

16 步端到端验证：
  客户→报价→订单→信用校验→价格匹配→审批→预留→WMS Picking→包装→发货
  →INV Transaction→结算→发票→收款→信用释放

另含部分发货黄金链路 100→30→40→30 四态守恒验证。
"""

from __future__ import annotations

import pytest

from app.application.e2e.sal_golden_path_e2e_suite import (
    SalGoldenPathE2ETestSuite,
    SalPartialFulfillmentE2ETestSuite,
)


@pytest.mark.asyncio
async def test_sal_golden_path_e2e_16_steps():
    """C-SAL-GOLDEN-01: SAL 黄金链路 16 步端到端验证。"""
    suite = SalGoldenPathE2ETestSuite()
    report = await suite.run()

    assert report.total_steps == 16, f"Expected 16 steps, got {report.total_steps}"
    assert report.all_passed, (
        f"SAL Golden path E2E failed: {report.failed_steps} steps failed. "
        f"Details: {report.to_dict()}"
    )
    assert report.passed_steps == 16
    assert report.failed_steps == 0


@pytest.mark.asyncio
async def test_sal_golden_path_e2e_report_structure():
    """验证 SAL E2E 测试报告结构完整性。"""
    suite = SalGoldenPathE2ETestSuite()
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


@pytest.mark.asyncio
async def test_sal_partial_fulfillment_100_30_40_30():
    """SAL 部分发货黄金链路 100→30→40→30 四态守恒验证。"""
    suite = SalPartialFulfillmentE2ETestSuite()
    report = await suite.run()

    assert report.total_steps == 6, f"Expected 6 steps, got {report.total_steps}"
    assert report.all_passed, (
        f"SAL Partial fulfillment E2E failed: {report.failed_steps} steps failed. "
        f"Details: {report.to_dict()}"
    )
    assert report.passed_steps == 6
    assert report.failed_steps == 0


@pytest.mark.asyncio
async def test_sal_golden_path_red_line_verification():
    """验证 SAL 黄金链路三条红线：
    - 红线一：销售出库通过 WMS Picking/Shipping API
    - 红线二：销售结算通过 INV Financial API
    - 红线五：库存预留通过 INV Reservation API
    """
    suite = SalGoldenPathE2ETestSuite()
    report = await suite.run()

    results = {r.step_number: r for r in report.results}

    assert results[11].passed, "红线五: 确认履约应通过 INV Reservation API 预留"
    assert "INV Reservation" in results[11].step_name or "Reservation" in results[11].step_name

    assert results[12].passed, "红线一: 发货应通过 WMS Picking API"
    assert "WMS Picking" in results[12].step_name

    assert results[14].passed, "红线一: 确认发货应通过 WMS Shipping API"
    assert "WMS Shipping" in results[14].step_name

    assert results[15].passed, "红线二: 结算应通过 INV Financial API"
    assert "INV Financial" in results[15].step_name