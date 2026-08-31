"""上架策略服务 - 库位建议排序，策略模式实现。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.warehouse.value_objects.wms_config import PutawayStrategy


@dataclass(frozen=True)
class LocationCandidate:
    """库位候选 - 上架策略服务的输入/输出。"""
    location_id: UUID
    location_code: str
    zone_function: str
    existing_sku_qty: float = 0.0
    distance: float | None = None
    turnover_rate: float = 0.0
    available_capacity: float | None = None


class PutawayStrategyService:
    """上架策略领域服务 - 输入 sku_id/quantity/strategy，输出建议库位排序列表。

    P0 实现四种基础策略：
    - SAME_PRODUCT_CONCENTRATE: 优先已有该 SKU 的库位
    - NEAREST: 按坐标距离排序
    - ZONED: 按库区功能匹配
    - BY_TURNOVER: 按历史周转率排序

    P1 扩展 FEFO/路径优化只需新增策略实现，不修改作业应用服务。
    """

    @staticmethod
    def suggest(
        candidates: list[LocationCandidate],
        strategy: PutawayStrategy,
    ) -> list[LocationCandidate]:
        """根据策略对库位候选排序，返回建议库位列表。"""
        if strategy == PutawayStrategy.SAME_PRODUCT_CONCENTRATE:
            return PutawayStrategyService._same_product_concentrate(candidates)
        elif strategy == PutawayStrategy.NEAREST:
            return PutawayStrategyService._nearest(candidates)
        elif strategy == PutawayStrategy.ZONED:
            return PutawayStrategyService._zoned(candidates)
        elif strategy == PutawayStrategy.BY_TURNOVER:
            return PutawayStrategyService._by_turnover(candidates)
        else:
            return list(candidates)

    @staticmethod
    def _same_product_concentrate(candidates: list[LocationCandidate]) -> list[LocationCandidate]:
        """同品集中 - 优先已有该 SKU 的库位。"""
        return sorted(candidates, key=lambda c: -c.existing_sku_qty)

    @staticmethod
    def _nearest(candidates: list[LocationCandidate]) -> list[LocationCandidate]:
        """就近上架 - 按坐标距离排序。"""
        return sorted(candidates, key=lambda c: c.distance if c.distance is not None else float('inf'))

    @staticmethod
    def _zoned(candidates: list[LocationCandidate]) -> list[LocationCandidate]:
        """分区上架 - 按库区功能匹配（STORAGE 优先）。"""
        priority = {"storage": 0, "picking": 1, "receiving": 2, "qc": 3, "shipping": 4, "blocked": 5}
        return sorted(candidates, key=lambda c: priority.get(c.zone_function, 99))

    @staticmethod
    def _by_turnover(candidates: list[LocationCandidate]) -> list[LocationCandidate]:
        """按周转率上架 - 按历史周转率排序（高周转优先）。"""
        return sorted(candidates, key=lambda c: -c.turnover_rate)