"""REL 封版 Prometheus 指标注册。"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

_METRIC_PREFIX = "eitp"


class RELMetricsRegistry:
    """REL 封版指标注册中心 - 命名 eitp_rel_{metric}_{type}。"""

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._init_rel_metrics()

    def _init_rel_metrics(self) -> None:
        self._counters["rel_seal_gate_total"] = Counter(
            f"{_METRIC_PREFIX}_rel_seal_gate_total",
            "封版门禁执行总数",
            ["gate_type", "result"],
        )
        self._histograms["rel_asset_snapshot_duration_seconds"] = Histogram(
            f"{_METRIC_PREFIX}_rel_asset_snapshot_duration_seconds",
            "资产快照采集耗时",
            ["asset_type"],
            buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        )
        self._gauges["rel_seal_status"] = Gauge(
            f"{_METRIC_PREFIX}_rel_seal_status",
            "封版状态（0=REQUESTED...5=SEALED）",
            ["release_id"],
        )
        self._gauges["rel_core_freeze_verification_result"] = Gauge(
            f"{_METRIC_PREFIX}_rel_core_freeze_verification_result",
            "核心冻结校验结果（0=PASS/1=FAIL）",
        )
        self._gauges["rel_rollback_drill_status"] = Gauge(
            f"{_METRIC_PREFIX}_rel_rollback_drill_status",
            "回滚演练状态（0=NOT_DRILLED/1=PASS/2=FAIL）",
            ["rollback_id"],
        )
        self._counters["rel_asset_snapshot_tamper_total"] = Counter(
            f"{_METRIC_PREFIX}_rel_asset_snapshot_tamper_total",
            "资产快照篡改总数",
            ["asset_type"],
        )

    def record_gate(self, gate_type: str, result: str) -> None:
        self._counters["rel_seal_gate_total"].labels(gate_type=gate_type, result=result).inc()

    def observe_snapshot_duration(self, asset_type: str, duration: float) -> None:
        self._histograms["rel_asset_snapshot_duration_seconds"].labels(asset_type=asset_type).observe(duration)

    def set_seal_status(self, release_id: str, status: int) -> None:
        self._gauges["rel_seal_status"].labels(release_id=release_id).set(status)

    def set_core_freeze_result(self, passed: bool) -> None:
        self._gauges["rel_core_freeze_verification_result"].set(0 if passed else 1)

    def set_rollback_drill_status(self, rollback_id: str, status: int) -> None:
        self._gauges["rel_rollback_drill_status"].labels(rollback_id=rollback_id).set(status)

    def record_snapshot_tamper(self, asset_type: str) -> None:
        self._counters["rel_asset_snapshot_tamper_total"].labels(asset_type=asset_type).inc()


_registry: RELMetricsRegistry | None = None


def get_rel_metrics_registry() -> RELMetricsRegistry:
    global _registry
    if _registry is None:
        _registry = RELMetricsRegistry()
    return _registry