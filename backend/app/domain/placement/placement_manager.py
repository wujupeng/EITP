"""放置管理器 - 按 tenant_id 路由数据源与大客户迁移建议。

spec 5.7.1 规则 4: 大客户独立放置触发。
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.placement.placement_record import PlacementRecord, PlacementType


@dataclass(frozen=True)
class TenantScaleMetrics:
    """租户规模指标 - 用于大客户迁移建议评估。

    阈值（spec 5.7.1 规则 4）：500 万订单 / 100 仓库 / 10 万 SKU / 3000 用户。
    """

    tenant_id: UUID
    order_count: int = 0
    warehouse_count: int = 0
    sku_count: int = 0
    user_count: int = 0

    _ORDER_THRESHOLD = 5_000_000
    _WAREHOUSE_THRESHOLD = 100
    _SKU_THRESHOLD = 100_000
    _USER_THRESHOLD = 3_000

    def exceeds_threshold(self) -> bool:
        """是否超过大客户阈值。"""
        return (
            self.order_count >= self._ORDER_THRESHOLD
            or self.warehouse_count >= self._WAREHOUSE_THRESHOLD
            or self.sku_count >= self._SKU_THRESHOLD
            or self.user_count >= self._USER_THRESHOLD
        )

    def threshold_details(self) -> dict:
        """返回超阈值的指标详情。"""
        details: dict = {}
        if self.order_count >= self._ORDER_THRESHOLD:
            details["order_count"] = {"current": self.order_count, "threshold": self._ORDER_THRESHOLD}
        if self.warehouse_count >= self._WAREHOUSE_THRESHOLD:
            details["warehouse_count"] = {"current": self.warehouse_count, "threshold": self._WAREHOUSE_THRESHOLD}
        if self.sku_count >= self._SKU_THRESHOLD:
            details["sku_count"] = {"current": self.sku_count, "threshold": self._SKU_THRESHOLD}
        if self.user_count >= self._USER_THRESHOLD:
            details["user_count"] = {"current": self.user_count, "threshold": self._USER_THRESHOLD}
        return details


@dataclass(frozen=True)
class MigrationSuggestion:
    """迁移建议 - 大客户超阈值时生成。"""

    tenant_id: UUID
    suggested_placement: PlacementType
    reason: str
    exceeded_metrics: dict


class PlacementManager:
    """放置管理器 - 路由数据源与评估迁移建议。

    职责：
    - 按 tenant_id 路由至对应数据源
    - 评估大客户迁移建议
    - 切换放置模式（原子更新 + 连接池缓存失效）
    """

    def __init__(self) -> None:
        self._records: dict[UUID, PlacementRecord] = {}
        self._connection_cache: dict[UUID, str] = {}

    def get_placement(self, tenant_id: UUID) -> PlacementRecord | None:
        return self._records.get(tenant_id)

    def set_placement(
        self,
        tenant_id: UUID,
        placement: PlacementType,
    ) -> PlacementRecord:
        """设置放置模式 - 原子更新并失效连接缓存。"""
        record = PlacementRecord.create(tenant_id, placement)
        self._records[tenant_id] = record
        self._connection_cache.pop(tenant_id, None)
        return record

    def get_connection_target(self, tenant_id: UUID) -> str:
        """获取连接目标 - 带缓存。"""
        if tenant_id in self._connection_cache:
            return self._connection_cache[tenant_id]

        record = self._records.get(tenant_id)
        if record is None:
            target = PlacementRecord.create(
                tenant_id, PlacementType.SHARED_DB
            ).connection_target
        else:
            target = record.connection_target

        self._connection_cache[tenant_id] = target
        return target

    def invalidate_cache(self, tenant_id: UUID) -> None:
        """失效连接缓存。"""
        self._connection_cache.pop(tenant_id, None)

    def evaluate_migration_suggestion(
        self,
        metrics: TenantScaleMetrics,
    ) -> MigrationSuggestion | None:
        """评估大客户迁移建议。

        spec 5.7.1 规则 4: 规模超阈值时建议迁移至独立数据库或独立实例。
        """
        if not metrics.exceeds_threshold():
            return None

        if metrics.order_count >= 10_000_000:
            suggested = PlacementType.DEDICATED_INSTANCE
        else:
            suggested = PlacementType.DEDICATED_DB

        return MigrationSuggestion(
            tenant_id=metrics.tenant_id,
            suggested_placement=suggested,
            reason="租户规模超过大客户阈值，建议迁移至独立放置",
            exceeded_metrics=metrics.threshold_details(),
        )