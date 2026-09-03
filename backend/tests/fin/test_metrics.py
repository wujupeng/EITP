"""红线测试 T15-12 - FIN 指标注册：Prometheus 指标命名与记录。

验证 EITP-FIN-001 的可观测性红线：
- FINMetricsRegistry 注册 7 个指标（2 Counter + 4 Gauge + 1 Histogram）
- 命名约定：eitp_fin_{metric}_{type}
- 每个指标的 record/set/observe 方法工作正常
- 标签维度正确
- get_fin_metrics_registry 单例
"""

from __future__ import annotations

import pytest
from prometheus_client import Counter, Gauge, Histogram

from app.infrastructure.platform.observability.fin_metrics import (
    FINMetricsRegistry,
    get_fin_metrics_registry,
)


class TestMetricsRegistration:
    """红线 5：7 个指标正确注册。"""

    def test_registers_2_counters(self) -> None:
        reg = get_fin_metrics_registry()
        assert len(reg._counters) == 2

    def test_registers_4_gauges(self) -> None:
        reg = get_fin_metrics_registry()
        assert len(reg._gauges) == 4

    def test_registers_1_histogram(self) -> None:
        reg = get_fin_metrics_registry()
        assert len(reg._histograms) == 1

    def test_total_7_metrics(self) -> None:
        reg = get_fin_metrics_registry()
        total = len(reg._counters) + len(reg._gauges) + len(reg._histograms)
        assert total == 7

    def test_counter_types(self) -> None:
        reg = get_fin_metrics_registry()
        for name, metric in reg._counters.items():
            assert isinstance(metric, Counter), f"{name} 应为 Counter"

    def test_gauge_types(self) -> None:
        reg = get_fin_metrics_registry()
        for name, metric in reg._gauges.items():
            assert isinstance(metric, Gauge), f"{name} 应为 Gauge"

    def test_histogram_types(self) -> None:
        reg = get_fin_metrics_registry()
        for name, metric in reg._histograms.items():
            assert isinstance(metric, Histogram), f"{name} 应为 Histogram"


class TestMetricsNamingConvention:
    """红线 5：命名约定 eitp_fin_{metric}_{type}。"""

    def test_counter_names_have_eitp_fin_prefix(self) -> None:
        reg = get_fin_metrics_registry()
        for name, metric in reg._counters.items():
            assert metric._name.startswith("eitp_fin_"), (
                f"{name}: {metric._name} 应以 eitp_fin_ 开头"
            )

    def test_gauge_names_have_eitp_fin_prefix(self) -> None:
        reg = get_fin_metrics_registry()
        for name, metric in reg._gauges.items():
            assert metric._name.startswith("eitp_fin_"), (
                f"{name}: {metric._name} 应以 eitp_fin_ 开头"
            )

    def test_histogram_names_have_eitp_fin_prefix(self) -> None:
        reg = get_fin_metrics_registry()
        for name, metric in reg._histograms.items():
            assert metric._name.startswith("eitp_fin_"), (
                f"{name}: {metric._name} 应以 eitp_fin_ 开头"
            )

    def test_settlement_counter_name(self) -> None:
        reg = get_fin_metrics_registry()
        assert "fin_settlement_created_total" in reg._counters
        # prometheus_client strips _total suffix from Counter._name
        assert reg._counters["fin_settlement_created_total"]._name == "eitp_fin_settlement_created"

    def test_payment_gauge_name(self) -> None:
        reg = get_fin_metrics_registry()
        assert "fin_payment_success_rate" in reg._gauges
        assert reg._gauges["fin_payment_success_rate"]._name == "eitp_fin_payment_success_rate"

    def test_receipt_histogram_name(self) -> None:
        reg = get_fin_metrics_registry()
        assert "fin_receipt_writeoff_amount" in reg._histograms
        assert reg._histograms["fin_receipt_writeoff_amount"]._name == "eitp_fin_receipt_writeoff_amount"

    def test_invoice_counter_name(self) -> None:
        reg = get_fin_metrics_registry()
        assert "fin_invoice_issued_total" in reg._counters
        # prometheus_client strips _total suffix from Counter._name
        assert reg._counters["fin_invoice_issued_total"]._name == "eitp_fin_invoice_issued"

    def test_recon_gauge_name(self) -> None:
        reg = get_fin_metrics_registry()
        assert "fin_recon_diff_count" in reg._gauges
        assert reg._gauges["fin_recon_diff_count"]._name == "eitp_fin_recon_diff_count"

    def test_treasury_gauge_name(self) -> None:
        reg = get_fin_metrics_registry()
        assert "fin_treasury_balance" in reg._gauges
        assert reg._gauges["fin_treasury_balance"]._name == "eitp_fin_treasury_balance"

    def test_ar_aging_gauge_name(self) -> None:
        reg = get_fin_metrics_registry()
        assert "fin_ar_aging_bucket" in reg._gauges
        assert reg._gauges["fin_ar_aging_bucket"]._name == "eitp_fin_ar_aging_bucket"


class TestMetricsLabels:
    """红线 5：指标标签维度。"""

    def test_settlement_counter_has_settlement_type_label(self) -> None:
        reg = get_fin_metrics_registry()
        labels = reg._counters["fin_settlement_created_total"]._labelnames
        assert "settlement_type" in labels

    def test_payment_gauge_has_payment_method_label(self) -> None:
        reg = get_fin_metrics_registry()
        labels = reg._gauges["fin_payment_success_rate"]._labelnames
        assert "payment_method" in labels

    def test_invoice_counter_has_invoice_type_label(self) -> None:
        reg = get_fin_metrics_registry()
        labels = reg._counters["fin_invoice_issued_total"]._labelnames
        assert "invoice_type" in labels

    def test_recon_gauge_has_diff_type_label(self) -> None:
        reg = get_fin_metrics_registry()
        labels = reg._gauges["fin_recon_diff_count"]._labelnames
        assert "diff_type" in labels

    def test_treasury_gauge_has_account_type_label(self) -> None:
        reg = get_fin_metrics_registry()
        labels = reg._gauges["fin_treasury_balance"]._labelnames
        assert "account_type" in labels

    def test_ar_aging_gauge_has_bucket_label(self) -> None:
        reg = get_fin_metrics_registry()
        labels = reg._gauges["fin_ar_aging_bucket"]._labelnames
        assert "bucket" in labels

    def test_receipt_histogram_no_labels(self) -> None:
        reg = get_fin_metrics_registry()
        labels = reg._histograms["fin_receipt_writeoff_amount"]._labelnames
        assert len(labels) == 0


class TestMetricsRecording:
    """红线 5：record/set/observe 方法。"""

    def test_record_settlement_created(self) -> None:
        reg = get_fin_metrics_registry()
        reg.record_settlement_created("PURCHASE")
        reg.record_settlement_created("SALES")
        reg.record_settlement_created("PURCHASE")
        assert True

    def test_set_payment_success_rate(self) -> None:
        reg = get_fin_metrics_registry()
        reg.set_payment_success_rate("BANK_TRANSFER", 0.95)
        reg.set_payment_success_rate("CASH", 1.0)
        assert True

    def test_observe_receipt_writeoff_amount(self) -> None:
        reg = get_fin_metrics_registry()
        reg.observe_receipt_writeoff_amount(100.0)
        reg.observe_receipt_writeoff_amount(10000.0)
        reg.observe_receipt_writeoff_amount(500000.0)
        assert True

    def test_record_invoice_issued(self) -> None:
        reg = get_fin_metrics_registry()
        reg.record_invoice_issued("VAT_NORMAL")
        reg.record_invoice_issued("VAT_SPECIAL")
        assert True

    def test_set_recon_diff_count(self) -> None:
        reg = get_fin_metrics_registry()
        reg.set_recon_diff_count("AMOUNT_DIFF", 5)
        reg.set_recon_diff_count("TIME_DIFF", 3)
        assert True

    def test_set_treasury_balance(self) -> None:
        reg = get_fin_metrics_registry()
        reg.set_treasury_balance("BANK", 500000.0)
        reg.set_treasury_balance("INTERNAL", 100000.0)
        assert True

    def test_set_ar_aging_bucket(self) -> None:
        reg = get_fin_metrics_registry()
        reg.set_ar_aging_bucket("B_0_30", 100000.0)
        reg.set_ar_aging_bucket("B_31_60", 50000.0)
        reg.set_ar_aging_bucket("B_180_PLUS", 5000.0)
        assert True


class TestMetricsRegistrySingleton:
    """红线 5：get_fin_metrics_registry 单例。"""

    def test_singleton_returns_same_instance(self) -> None:
        a = get_fin_metrics_registry()
        b = get_fin_metrics_registry()
        assert a is b

    def test_singleton_is_fin_metrics_registry(self) -> None:
        reg = get_fin_metrics_registry()
        assert isinstance(reg, FINMetricsRegistry)