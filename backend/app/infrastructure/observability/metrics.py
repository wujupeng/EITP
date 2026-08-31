"""INV 监控指标定义与 Prometheus 暴露端点。

对应 design 2.7.3 - 8 个核心指标：
  - inv_transaction_tps（Counter）
  - inv_transaction_duration_ms（Histogram）
  - inv_idempotency_hit_count（Counter）
  - inv_negative_stock_triggered（Counter）
  - inv_reservation_expired（Counter）
  - inv_balance_snapshot_inconsistent（Counter）
  - inv_ledger_append_failed（Counter）
  - inv_balance_query_duration_ms（Histogram）

所有指标按 tenant_id / warehouse_id 维度聚合。
"""

from __future__ import annotations

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from fastapi import FastAPI, Response


# ---------------------------------------------------------------------------
# Counter 指标
# ---------------------------------------------------------------------------

inv_transaction_tps = Counter(
    "inv_transaction_tps",
    "库存事务处理总数",
    labelnames=("tenant_id", "warehouse_id", "transaction_type", "status"),
)

inv_idempotency_hit_count = Counter(
    "inv_idempotency_hit_count",
    "幂等命中次数（重复请求被拦截）",
    labelnames=("tenant_id", "transaction_type"),
)

inv_negative_stock_triggered = Counter(
    "inv_negative_stock_triggered",
    "负库存策略触发次数",
    labelnames=("tenant_id", "warehouse_id", "policy_mode"),
)

inv_reservation_expired = Counter(
    "inv_reservation_expired",
    "库存预留过期释放次数",
    labelnames=("tenant_id", "warehouse_id"),
)

inv_balance_snapshot_inconsistent = Counter(
    "inv_balance_snapshot_inconsistent",
    "余额快照不一致检测次数",
    labelnames=("tenant_id", "warehouse_id", "sku_id"),
)

inv_ledger_append_failed = Counter(
    "inv_ledger_append_failed",
    "账本追加失败次数",
    labelnames=("tenant_id", "warehouse_id", "reason"),
)


# ---------------------------------------------------------------------------
# Histogram 指标
# ---------------------------------------------------------------------------

inv_transaction_duration_ms = Histogram(
    "inv_transaction_duration_ms",
    "库存事务执行耗时（毫秒）",
    labelnames=("tenant_id", "warehouse_id", "transaction_type"),
    buckets=(
        5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000,
    ),
)

inv_balance_query_duration_ms = Histogram(
    "inv_balance_query_duration_ms",
    "库存余额查询耗时（毫秒）",
    labelnames=("tenant_id", "warehouse_id"),
    buckets=(
        1, 5, 10, 25, 50, 100, 250, 500, 1000,
    ),
)


# ---------------------------------------------------------------------------
# 便捷埋点函数
# ---------------------------------------------------------------------------

def record_transaction(
    tenant_id: str,
    warehouse_id: str,
    transaction_type: str,
    duration_ms: float,
    status: str = "success",
) -> None:
    """记录一次库存事务的指标。"""
    inv_transaction_tps.labels(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
        status=status,
    ).inc()
    inv_transaction_duration_ms.labels(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
    ).observe(duration_ms)


def record_idempotency_hit(tenant_id: str, transaction_type: str) -> None:
    """记录幂等命中。"""
    inv_idempotency_hit_count.labels(
        tenant_id=tenant_id,
        transaction_type=transaction_type,
    ).inc()


def record_negative_stock(
    tenant_id: str, warehouse_id: str, policy_mode: str
) -> None:
    """记录负库存触发。"""
    inv_negative_stock_triggered.labels(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        policy_mode=policy_mode,
    ).inc()


def record_reservation_expired(tenant_id: str, warehouse_id: str) -> None:
    """记录预留过期。"""
    inv_reservation_expired.labels(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
    ).inc()


def record_balance_inconsistent(
    tenant_id: str, warehouse_id: str, sku_id: str
) -> None:
    """记录余额不一致。"""
    inv_balance_snapshot_inconsistent.labels(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        sku_id=sku_id,
    ).inc()


def record_ledger_append_failed(
    tenant_id: str, warehouse_id: str, reason: str
) -> None:
    """记录账本追加失败。"""
    inv_ledger_append_failed.labels(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
        reason=reason,
    ).inc()


def record_balance_query(tenant_id: str, warehouse_id: str, duration_ms: float) -> None:
    """记录余额查询耗时。"""
    inv_balance_query_duration_ms.labels(
        tenant_id=tenant_id,
        warehouse_id=warehouse_id,
    ).observe(duration_ms)


# ---------------------------------------------------------------------------
# MDM 监控指标（14 个，对应 design 2.9.3）
# ---------------------------------------------------------------------------

mdm_group_product_query_qps = Counter(
    "mdm_group_product_query_qps",
    "集团商品目录查询次数",
    labelnames=("tenant_id", "scope"),
)

mdm_enterprise_product_query_qps = Counter(
    "mdm_enterprise_product_query_qps",
    "企业商品查询次数",
    labelnames=("tenant_id",),
)

mdm_master_data_detail_query_duration_ms = Histogram(
    "mdm_master_data_detail_query_duration_ms",
    "商品主数据详情查询耗时（毫秒）",
    labelnames=("tenant_id",),
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
)

mdm_barcode_locate_duration_ms = Histogram(
    "mdm_barcode_locate_duration_ms",
    "条码定位 SKU 耗时（毫秒）",
    labelnames=("tenant_id",),
    buckets=(1, 5, 10, 25, 50, 100, 250, 500),
)

mdm_governance_submit_tps = Counter(
    "mdm_governance_submit_tps",
    "主数据变更申请提交次数",
    labelnames=("tenant_id", "entity_type", "governance_level"),
)

mdm_governance_publish_duration_ms = Histogram(
    "mdm_governance_publish_duration_ms",
    "主数据发布耗时（毫秒）",
    labelnames=("tenant_id", "entity_type"),
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000),
)

mdm_version_compare_duration_ms = Histogram(
    "mdm_version_compare_duration_ms",
    "版本对比耗时（毫秒）",
    labelnames=("tenant_id",),
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000),
)

mdm_governance_approval_pending_count = Gauge(
    "mdm_governance_approval_pending_count",
    "待审批变更申请数量",
    labelnames=("governance_level",),
)

mdm_version_publish_count = Counter(
    "mdm_version_publish_count",
    "版本发布次数",
    labelnames=("tenant_id", "entity_type"),
)

mdm_negative_policy_change_count = Counter(
    "mdm_negative_policy_change_count",
    "负库存策略变更次数",
    labelnames=("tenant_id", "from_policy", "to_policy"),
)

mdm_product_reference_count = Gauge(
    "mdm_product_reference_count",
    "商品引用关系数量",
    labelnames=("tenant_id",),
)

mdm_governance_rollback_count = Counter(
    "mdm_governance_rollback_count",
    "治理工作流回滚次数",
    labelnames=("tenant_id", "entity_type"),
)

mdm_group_product_disabled_with_reference_count = Counter(
    "mdm_group_product_disabled_with_reference_count",
    "集团商品停用但仍有活跃引用次数",
    labelnames=("group_product_id",),
)

mdm_e2e_golden_path_result = Gauge(
    "mdm_e2e_golden_path_result",
    "黄金链路 E2E 测试结果（1=通过, 0=失败）",
    labelnames=(),
)


# ---------------------------------------------------------------------------
# MDM 便捷埋点函数
# ---------------------------------------------------------------------------

def record_mdm_group_product_query(tenant_id: str, scope: str = "group") -> None:
    mdm_group_product_query_qps.labels(tenant_id=tenant_id, scope=scope).inc()

def record_mdm_enterprise_product_query(tenant_id: str) -> None:
    mdm_enterprise_product_query_qps.labels(tenant_id=tenant_id).inc()

def record_mdm_master_data_detail_query(tenant_id: str, duration_ms: float) -> None:
    mdm_master_data_detail_query_duration_ms.labels(tenant_id=tenant_id).observe(duration_ms)

def record_mdm_barcode_locate(tenant_id: str, duration_ms: float) -> None:
    mdm_barcode_locate_duration_ms.labels(tenant_id=tenant_id).observe(duration_ms)

def record_mdm_governance_submit(tenant_id: str, entity_type: str, governance_level: str) -> None:
    mdm_governance_submit_tps.labels(
        tenant_id=tenant_id, entity_type=entity_type, governance_level=governance_level
    ).inc()

def record_mdm_governance_publish(tenant_id: str, entity_type: str, duration_ms: float) -> None:
    mdm_governance_publish_duration_ms.labels(
        tenant_id=tenant_id, entity_type=entity_type
    ).observe(duration_ms)
    mdm_version_publish_count.labels(tenant_id=tenant_id, entity_type=entity_type).inc()

def record_mdm_version_compare(tenant_id: str, duration_ms: float) -> None:
    mdm_version_compare_duration_ms.labels(tenant_id=tenant_id).observe(duration_ms)

def set_mdm_governance_approval_pending(governance_level: str, count: int) -> None:
    mdm_governance_approval_pending_count.labels(governance_level=governance_level).set(count)

def record_mdm_negative_policy_change(tenant_id: str, from_policy: str, to_policy: str) -> None:
    mdm_negative_policy_change_count.labels(
        tenant_id=tenant_id, from_policy=from_policy, to_policy=to_policy
    ).inc()

def set_mdm_product_reference_count(tenant_id: str, count: int) -> None:
    mdm_product_reference_count.labels(tenant_id=tenant_id).set(count)

def record_mdm_governance_rollback(tenant_id: str, entity_type: str) -> None:
    mdm_governance_rollback_count.labels(tenant_id=tenant_id, entity_type=entity_type).inc()

def record_mdm_group_product_disabled_with_reference(group_product_id: str) -> None:
    mdm_group_product_disabled_with_reference_count.labels(group_product_id=group_product_id).inc()

def set_mdm_e2e_golden_path_result(passed: bool) -> None:
    mdm_e2e_golden_path_result.set(1 if passed else 0)


# ---------------------------------------------------------------------------
# WMS 指标（9 个）
# ---------------------------------------------------------------------------

wms_task_created_total = Counter(
    "wms_task_created_total",
    "WMS Task 创建总数",
    labelnames=["tenant_id", "warehouse_id", "task_type"],
)

wms_task_completed_total = Counter(
    "wms_task_completed_total",
    "WMS Task 完成总数",
    labelnames=["tenant_id", "warehouse_id", "task_type", "status"],
)

wms_task_duration_ms = Histogram(
    "wms_task_duration_ms",
    "WMS Task 执行耗时（毫秒）",
    labelnames=["tenant_id", "warehouse_id", "task_type"],
)

wms_task_backlog = Gauge(
    "wms_task_backlog",
    "WMS Task 积压数",
    labelnames=["tenant_id", "warehouse_id", "status"],
)

wms_putaway_suggestion_hit_rate = Gauge(
    "wms_putaway_suggestion_hit_rate",
    "上架库位建议命中率",
    labelnames=["tenant_id", "warehouse_id"],
)

wms_picking_strategy_split_count = Histogram(
    "wms_picking_strategy_split_count",
    "拣货策略拆分次数",
    labelnames=["tenant_id", "warehouse_id", "strategy"],
)

wms_inv_reconcile_diff_total = Counter(
    "wms_inv_reconcile_diff_total",
    "WMS↔INV 对账差异总数",
    labelnames=["tenant_id", "warehouse_id"],
)

wms_inv_transaction_failed_total = Counter(
    "wms_inv_transaction_failed_total",
    "WMS 调用 INV Transaction 失败总数",
    labelnames=["tenant_id", "warehouse_id", "task_type"],
)

wms_position_query_duration_ms = Histogram(
    "wms_position_query_duration_ms",
    "库存位置查询耗时（毫秒）",
    labelnames=["tenant_id"],
)

wms_e2e_golden_path_result = Gauge(
    "wms_e2e_golden_path_result",
    "WMS 黄金链路 E2E 测试结果（1=通过, 0=失败）",
    labelnames=(),
)


# ---------------------------------------------------------------------------
# WMS 便捷埋点函数
# ---------------------------------------------------------------------------

def record_wms_task_created(tenant_id: str, warehouse_id: str, task_type: str) -> None:
    wms_task_created_total.labels(tenant_id=tenant_id, warehouse_id=warehouse_id, task_type=task_type).inc()

def record_wms_task_completed(tenant_id: str, warehouse_id: str, task_type: str, status: str) -> None:
    wms_task_completed_total.labels(
        tenant_id=tenant_id, warehouse_id=warehouse_id, task_type=task_type, status=status
    ).inc()

def record_wms_task_duration(tenant_id: str, warehouse_id: str, task_type: str, duration_ms: float) -> None:
    wms_task_duration_ms.labels(
        tenant_id=tenant_id, warehouse_id=warehouse_id, task_type=task_type
    ).observe(duration_ms)

def set_wms_task_backlog(tenant_id: str, warehouse_id: str, status: str, count: float) -> None:
    wms_task_backlog.labels(tenant_id=tenant_id, warehouse_id=warehouse_id, status=status).set(count)

def set_wms_putaway_hit_rate(tenant_id: str, warehouse_id: str, rate: float) -> None:
    wms_putaway_suggestion_hit_rate.labels(tenant_id=tenant_id, warehouse_id=warehouse_id).set(rate)

def record_wms_picking_split(tenant_id: str, warehouse_id: str, strategy: str, split_count: int) -> None:
    wms_picking_strategy_split_count.labels(
        tenant_id=tenant_id, warehouse_id=warehouse_id, strategy=strategy
    ).observe(split_count)

def record_wms_reconcile_diff(tenant_id: str, warehouse_id: str) -> None:
    wms_inv_reconcile_diff_total.labels(tenant_id=tenant_id, warehouse_id=warehouse_id).inc()

def record_wms_inv_transaction_failed(tenant_id: str, warehouse_id: str, task_type: str) -> None:
    wms_inv_transaction_failed_total.labels(
        tenant_id=tenant_id, warehouse_id=warehouse_id, task_type=task_type
    ).inc()

def record_wms_position_query(tenant_id: str, duration_ms: float) -> None:
    wms_position_query_duration_ms.labels(tenant_id=tenant_id).observe(duration_ms)

def set_wms_e2e_golden_path_result(passed: bool) -> None:
    wms_e2e_golden_path_result.set(1 if passed else 0)


# ---------------------------------------------------------------------------
# Prometheus 暴露端点
# ---------------------------------------------------------------------------

def setup_metrics_endpoint(app: FastAPI) -> None:
    """在 FastAPI 应用上注册 /metrics 端点。"""

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)