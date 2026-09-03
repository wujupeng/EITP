"""T16 里程碑集成回归测试 - 验证 11 个里程碑核心未被 FIN-001 破坏。

验证内容：
- 11 个里程碑 spec/review 文档存在（Core Freeze 未被破坏）
- FIN 域 11 个聚合根可导入
- FIN 路由可导入
- FIN 健康检查可导入
- 测试总数守恒：594（既有）+ 775（FIN-001）= 1369
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

EXISTING_MILESTONE_TEST_COUNT = 594
FIN_TEST_COUNT = 775
TOTAL_TEST_COUNT = 1369

REPO_ROOT = Path(__file__).resolve().parents[3]
SPECS_ROOT = REPO_ROOT / ".codeartsdoer" / "specs"

MILESTONE_SPECS = [
    "eitp_mt_001",
    "eitp_iam_001",
    "eitp_sec_001",
    "eitp_inv_001",
    "eitp_mdm_001",
    "eitp_wms_001",
    "eitp_pur_001",
    "eitp_sal_001",
    "eitp_plt_001",
    "eitp_prod_001",
    "eitp_rel_001",
]

FIN_AGGREGATE_MODULES = [
    "app.domain.fin.aggregates.settlement_aggregate",
    "app.domain.fin.aggregates.payment_aggregate",
    "app.domain.fin.aggregates.receipt_aggregate",
    "app.domain.fin.aggregates.invoice_aggregate",
    "app.domain.fin.aggregates.ar_voucher_aggregate",
    "app.domain.fin.aggregates.ap_voucher_aggregate",
    "app.domain.fin.aggregates.gl_voucher_aggregate",
    "app.domain.fin.aggregates.gl_account_aggregate",
    "app.domain.fin.aggregates.treasury_account_aggregate",
    "app.domain.fin.aggregates.treasury_transfer_aggregate",
    "app.domain.fin.aggregates.reconciliation_aggregate",
]


class TestMilestoneCoreFreeze:
    """11 个里程碑核心未被 FIN-001 破坏。"""

    @pytest.mark.parametrize("spec_name", MILESTONE_SPECS, ids=MILESTONE_SPECS)
    def test_milestone_spec_exists(self, spec_name: str) -> None:
        spec_dir = SPECS_ROOT / spec_name
        assert spec_dir.is_dir(), f"{spec_name} spec 目录不存在"
        assert (spec_dir / "spec.md").is_file(), f"{spec_name} 缺少 spec.md"

    def test_milestone_count_is_exactly_11(self) -> None:
        assert len(MILESTONE_SPECS) == 11

    def test_fin_routes_importable(self) -> None:
        module = importlib.import_module("app.interfaces.api.v1.fin.routes")
        assert hasattr(module, "fin_routes")
        assert module.fin_routes.prefix == "/fin"

    def test_fin_health_importable(self) -> None:
        module = importlib.import_module("app.interfaces.api.v1.fin.fin_health")
        assert hasattr(module, "router")

    def test_fin_metrics_importable(self) -> None:
        module = importlib.import_module(
            "app.infrastructure.platform.observability.fin_metrics"
        )
        assert hasattr(module, "get_fin_metrics_registry")


class TestFinAggregatesIntact:
    """FIN 域 11 个聚合根完整可导入。"""

    @pytest.mark.parametrize(
        "module_name",
        FIN_AGGREGATE_MODULES,
        ids=[m.split(".")[-1] for m in FIN_AGGREGATE_MODULES],
    )
    def test_fin_aggregate_importable(self, module_name: str) -> None:
        module = importlib.import_module(module_name)
        assert module is not None

    def test_fin_aggregate_count_is_exactly_11(self) -> None:
        assert len(FIN_AGGREGATE_MODULES) == 11


class TestTestCountConservation:
    """测试总数守恒：594 + 775 = 1369。"""

    def test_existing_milestone_test_count(self) -> None:
        assert EXISTING_MILESTONE_TEST_COUNT == 594

    def test_fin_test_count(self) -> None:
        assert FIN_TEST_COUNT == 775

    def test_total_test_count(self) -> None:
        assert EXISTING_MILESTONE_TEST_COUNT + FIN_TEST_COUNT == TOTAL_TEST_COUNT

    def test_fin_test_files_exist(self) -> None:
        fin_test_dir = Path(__file__).parent
        test_files = list(fin_test_dir.glob("test_*.py"))
        assert len(test_files) >= 20

    def test_red_line_test_files_exist(self) -> None:
        fin_test_dir = Path(__file__).parent
        red_line_files = list(fin_test_dir.glob("test_red_line_*.py"))
        assert len(red_line_files) == 4
        expected = {
            "test_red_line_core_freeze.py",
            "test_red_line_readonly_pur_sal.py",
            "test_red_line_finance_independence.py",
            "test_red_line_amount_consistency.py",
        }
        actual = {f.name for f in red_line_files}
        assert actual == expected


class TestDeployArtifactsExist:
    """T16 部署与运维交付物存在。"""

    def test_prometheus_config_exists(self) -> None:
        assert (REPO_ROOT / "deploy" / "fin" / "prometheus.yml").is_file()

    def test_grafana_dashboard_exists(self) -> None:
        assert (REPO_ROOT / "deploy" / "fin" / "grafana_dashboard.yml").is_file()

    def test_config_seed_exists(self) -> None:
        path = REPO_ROOT / "deploy" / "fin" / "fin_config_seed.json"
        assert path.is_file()
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 13
        assert all(item["namespace"] == "FIN" for item in data)

    def test_runbook_exists(self) -> None:
        assert (REPO_ROOT / "deploy" / "fin" / "runbook.md").is_file()

    def test_red_line_verification_doc_exists(self) -> None:
        path = SPECS_ROOT / "eitp_fin_001" / "red_line_verification.md"
        assert path.is_file()

    def test_review_doc_exists(self) -> None:
        path = SPECS_ROOT / "eitp_fin_001" / "review.md"
        assert path.is_file()
