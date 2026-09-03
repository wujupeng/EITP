"""FIN 财务域 Prometheus 指标注册。"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

_METRIC_PREFIX = "eitp"


class FINMetricsRegistry:
    """FIN 财务域指标注册中心 - 命名 eitp_fin_{metric}_{type}。"""

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._init_fin_metrics()

    def _init_fin_metrics(self) -> None:
        self._counters["fin_settlement_created_total"] = Counter(
            f"{_METRIC_PREFIX}_fin_settlement_created_total",
            "结算单创建总数",
            ["settlement_type"],
        )
        self._gauges["fin_payment_success_rate"] = Gauge(
            f"{_METRIC_PREFIX}_fin_payment_success_rate",
            "付款执行成功率",
            ["payment_method"],
        )
        self._histograms["fin_receipt_writeoff_amount"] = Histogram(
            f"{_METRIC_PREFIX}_fin_receipt_writeoff_amount",
            "收款核销金额分布",
            buckets=(100, 1000, 10000, 50000, 100000, 500000, 1000000, 5000000),
        )
        self._counters["fin_invoice_issued_total"] = Counter(
            f"{_METRIC_PREFIX}_fin_invoice_issued_total",
            "发票开具总数",
            ["invoice_type"],
        )
        self._gauges["fin_recon_diff_count"] = Gauge(
            f"{_METRIC_PREFIX}_fin_recon_diff_count",
            "对账差异数量",
            ["diff_type"],
        )
        self._gauges["fin_treasury_balance"] = Gauge(
            f"{_METRIC_PREFIX}_fin_treasury_balance",
            "资金池账户余额",
            ["account_type"],
        )
        self._gauges["fin_ar_aging_bucket"] = Gauge(
            f"{_METRIC_PREFIX}_fin_ar_aging_bucket",
            "应收账龄分布金额",
            ["bucket"],
        )

    def record_settlement_created(self, settlement_type: str) -> None:
        self._counters["fin_settlement_created_total"].labels(settlement_type=settlement_type).inc()

    def set_payment_success_rate(self, payment_method: str, rate: float) -> None:
        self._gauges["fin_payment_success_rate"].labels(payment_method=payment_method).set(rate)

    def observe_receipt_writeoff_amount(self, amount: float) -> None:
        self._histograms["fin_receipt_writeoff_amount"].observe(amount)

    def record_invoice_issued(self, invoice_type: str) -> None:
        self._counters["fin_invoice_issued_total"].labels(invoice_type=invoice_type).inc()

    def set_recon_diff_count(self, diff_type: str, count: int) -> None:
        self._gauges["fin_recon_diff_count"].labels(diff_type=diff_type).set(count)

    def set_treasury_balance(self, account_type: str, balance: float) -> None:
        self._gauges["fin_treasury_balance"].labels(account_type=account_type).set(balance)

    def set_ar_aging_bucket(self, bucket: str, amount: float) -> None:
        self._gauges["fin_ar_aging_bucket"].labels(bucket=bucket).set(amount)


_registry: FINMetricsRegistry | None = None


def get_fin_metrics_registry() -> FINMetricsRegistry:
    global _registry
    if _registry is None:
        _registry = FINMetricsRegistry()
    return _registry