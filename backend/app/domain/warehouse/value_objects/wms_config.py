"""WMS 仓储策略配置值对象。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PutawayStrategy(str, Enum):
    """上架策略 - P0 基础策略 + P1 扩展。"""
    MANUAL = "manual"
    NEAREST = "nearest"
    EMPTY_FIRST = "empty_first"
    SAME_SKU = "same_sku"
    SAME_PRODUCT_CONCENTRATE = "same_product_concentrate"
    ZONED = "zoned"
    BY_TURNOVER = "by_turnover"


class PickingStrategy(str, Enum):
    """拣货策略 - P0 支持 FIFO+BY_LOCATION，P1 扩展 FEFO+BY_BATCH。"""
    FIFO = "fifo"
    LIFO = "lifo"
    FEFO = "fefo"
    MANUAL = "manual"
    BY_LOCATION = "by_location"
    BY_BATCH = "by_batch"


@dataclass(frozen=True)
class WmsConfig:
    """WMS 仓储策略配置 - 仓库级别的作业策略。"""

    putaway_strategy: PutawayStrategy = PutawayStrategy.MANUAL
    picking_strategy: PickingStrategy = PickingStrategy.FIFO
    receiving_over_receive_ratio: float = 0.0
    transfer_require_approval: bool = False

    def with_over_receive_ratio(self, ratio: float) -> WmsConfig:
        if ratio < 0:
            raise ValueError("over_receive_ratio must be >= 0")
        return WmsConfig(
            putaway_strategy=self.putaway_strategy,
            picking_strategy=self.picking_strategy,
            receiving_over_receive_ratio=ratio,
            transfer_require_approval=self.transfer_require_approval,
        )