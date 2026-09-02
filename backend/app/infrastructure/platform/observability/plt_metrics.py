"""平台指标注册中心 - 统一 Prometheus 指标命名规范。"""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest
from structlog import get_logger

logger = get_logger(__name__)

_METRIC_PREFIX = "eitp"


class PlatformMetricsRegistry:
    """平台指标注册中心 - 统一命名 eitp_{module}_{metric}_{type}。"""

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._infos: dict[str, Info] = {}
        self._init_platform_metrics()

    def _init_platform_metrics(self) -> None:
        self._counters["plt_api_requests_total"] = Counter(
            f"{_METRIC_PREFIX}_plt_api_requests_total",
            "PLT API 请求总数",
            ["tenant_id", "module", "operation", "status"],
        )
        self._histograms["plt_request_duration_seconds"] = Histogram(
            f"{_METRIC_PREFIX}_plt_request_duration_seconds",
            "PLT 请求延迟",
            ["tenant_id", "module", "operation"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        self._counters["plt_errors_total"] = Counter(
            f"{_METRIC_PREFIX}_plt_errors_total",
            "PLT 错误总数",
            ["tenant_id", "module", "error_code"],
        )
        self._gauges["plt_outbox_pending"] = Gauge(
            f"{_METRIC_PREFIX}_plt_outbox_pending",
            "Outbox 待投递事件数",
        )
        self._gauges["plt_saga_running"] = Gauge(
            f"{_METRIC_PREFIX}_plt_saga_running",
            "运行中 Saga 数",
        )
        self._gauges["plt_active_tenants"] = Gauge(
            f"{_METRIC_PREFIX}_plt_active_tenants",
            "活跃租户数",
        )
        self._histograms["plt_audit_write_duration_seconds"] = Histogram(
            f"{_METRIC_PREFIX}_plt_audit_write_duration_seconds",
            "审计写入延迟",
            buckets=(0.001, 0.002, 0.005, 0.01, 0.05),
        )
        self._counters["plt_outbox_delivered_total"] = Counter(
            f"{_METRIC_PREFIX}_plt_outbox_delivered_total",
            "Outbox 投递成功总数",
        )
        self._counters["plt_outbox_dead_letter_total"] = Counter(
            f"{_METRIC_PREFIX}_plt_outbox_dead_letter_total",
            "Outbox 死信总数",
        )
        self._counters["plt_idempotency_hits_total"] = Counter(
            f"{_METRIC_PREFIX}_plt_idempotency_hits_total",
            "幂等命中总数",
            ["tenant_id"],
        )
        self._counters["plt_rate_limited_total"] = Counter(
            f"{_METRIC_PREFIX}_plt_rate_limited_total",
            "限流拒绝总数",
            ["tenant_id", "api_path"],
        )

    def record_api_request(
        self,
        tenant_id: str,
        module: str,
        operation: str,
        status: str,
        duration: float,
    ) -> None:
        self._counters["plt_api_requests_total"].labels(
            tenant_id=tenant_id, module=module, operation=operation, status=status
        ).inc()
        self._histograms["plt_request_duration_seconds"].labels(
            tenant_id=tenant_id, module=module, operation=operation
        ).observe(duration)

    def record_error(self, tenant_id: str, module: str, error_code: str) -> None:
        self._counters["plt_errors_total"].labels(
            tenant_id=tenant_id, module=module, error_code=error_code
        ).inc()

    def set_outbox_pending(self, count: int) -> None:
        self._gauges["plt_outbox_pending"].set(count)

    def set_saga_running(self, count: int) -> None:
        self._gauges["plt_saga_running"].set(count)

    def record_outbox_delivered(self) -> None:
        self._counters["plt_outbox_delivered_total"].inc()

    def record_outbox_dead_letter(self) -> None:
        self._counters["plt_outbox_dead_letter_total"].inc()

    def record_idempotency_hit(self, tenant_id: str) -> None:
        self._counters["plt_idempotency_hits_total"].labels(tenant_id=tenant_id).inc()

    def record_rate_limited(self, tenant_id: str, api_path: str) -> None:
        self._counters["plt_rate_limited_total"].labels(
            tenant_id=tenant_id, api_path=api_path
        ).inc()

    def expose(self) -> bytes:
        return generate_latest()


_registry: PlatformMetricsRegistry | None = None


def get_metrics_registry() -> PlatformMetricsRegistry:
    global _registry
    if _registry is None:
        _registry = PlatformMetricsRegistry()
    return _registry