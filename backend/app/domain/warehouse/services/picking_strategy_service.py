"""拣货策略服务 - 库位选择 + 多库位拆分，策略模式实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.warehouse.value_objects.wms_config import PickingStrategy


@dataclass(frozen=True)
class PickableLocation:
    """可拣库位 - 拣货策略服务的输入。"""
    location_id: UUID
    location_code: str
    available_qty: float
    received_at: datetime | None = None
    expiry_date: datetime | None = None


@dataclass(frozen=True)
class PickingAllocation:
    """拣货分配 - 拣货策略服务的输出，含库位与数量。"""
    location_id: UUID
    location_code: str
    quantity: float


class PickingStrategyService:
    """拣货策略领域服务 - 输入 sku_id/quantity/strategy，输出拣货库位拆分方案。

    P0 实现：
    - FIFO: 按 received_at 入库时间先后
    - BY_LOCATION: 按库位编码排序
    - 多库位拆分: 如需 100 但单库位仅 60，拆分为两库位

    P1 扩展 FEFO（按效期先后）+ 路径优化（按 Coordinate 最短路径）。
    """

    @staticmethod
    def allocate(
        locations: list[PickableLocation],
        required_qty: float,
        strategy: PickingStrategy,
    ) -> list[PickingAllocation]:
        """根据策略选择库位并拆分，返回拣货分配方案。"""
        if strategy == PickingStrategy.FIFO:
            sorted_locs = PickingStrategyService._sort_fifo(locations)
        elif strategy == PickingStrategy.BY_LOCATION:
            sorted_locs = PickingStrategyService._sort_by_location(locations)
        elif strategy == PickingStrategy.FEFO:
            sorted_locs = PickingStrategyService._sort_fefo(locations)
        else:
            sorted_locs = list(locations)

        return PickingStrategyService._split_allocation(sorted_locs, required_qty)

    @staticmethod
    def _sort_fifo(locations: list[PickableLocation]) -> list[PickableLocation]:
        """FIFO - 按 received_at 入库时间先后排序。"""
        return sorted(locations, key=lambda l: l.received_at or datetime.max)

    @staticmethod
    def _sort_by_location(locations: list[PickableLocation]) -> list[PickableLocation]:
        """BY_LOCATION - 按库位编码排序。"""
        return sorted(locations, key=lambda l: l.location_code)

    @staticmethod
    def _sort_fefo(locations: list[PickableLocation]) -> list[PickableLocation]:
        """FEFO - 按效期先后排序（最早过期优先）。"""
        return sorted(locations, key=lambda l: l.expiry_date or datetime.max)

    @staticmethod
    def _split_allocation(
        sorted_locs: list[PickableLocation],
        required_qty: float,
    ) -> list[PickingAllocation]:
        """多库位拆分 - 从排序后的库位列表中依次分配数量。"""
        allocations: list[PickingAllocation] = []
        remaining = required_qty

        for loc in sorted_locs:
            if remaining <= 0:
                break
            if loc.available_qty <= 0:
                continue
            alloc_qty = min(remaining, loc.available_qty)
            allocations.append(PickingAllocation(
                location_id=loc.location_id,
                location_code=loc.location_code,
                quantity=alloc_qty,
            ))
            remaining -= alloc_qty

        return allocations