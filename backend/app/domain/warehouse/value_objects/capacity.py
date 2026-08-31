"""多维度容量值对象 - 件数/承重/体积三维度校验。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CapacityEnforceModeWms(str, Enum):
    """容量超限执行模式。"""
    WARN = "warn"
    REJECT = "reject"


@dataclass(frozen=True)
class Capacity:
    """多维度容量值对象 - 件数/承重/体积三维度。

    任一维度为 None 表示不限制该维度。
    """

    max_qty: float | None = None
    max_weight: float | None = None
    max_volume: float | None = None
    capacity_enforce_mode: CapacityEnforceModeWms = CapacityEnforceModeWms.WARN

    def check(
        self,
        add_qty: float = 0,
        add_weight: float = 0,
        add_volume: float = 0,
        current_qty: float = 0,
        current_weight: float = 0,
        current_volume: float = 0,
    ) -> CapacityCheckResult:
        """校验新增数量/重量/体积是否超出容量限制。"""
        exceeded_dims: list[str] = []

        if self.max_qty is not None and current_qty + add_qty > self.max_qty:
            exceeded_dims.append("qty")
        if self.max_weight is not None and current_weight + add_weight > self.max_weight:
            exceeded_dims.append("weight")
        if self.max_volume is not None and current_volume + add_volume > self.max_volume:
            exceeded_dims.append("volume")

        exceeded = len(exceeded_dims) > 0
        allowed = not exceeded or self.capacity_enforce_mode == CapacityEnforceModeWms.WARN

        message = ""
        if exceeded:
            message = f"容量超限: {', '.join(exceeded_dims)}"

        return CapacityCheckResult(
            allowed=allowed,
            exceeded=exceeded,
            exceeded_dims=exceeded_dims,
            message=message,
        )


@dataclass(frozen=True)
class CapacityCheckResult:
    """容量校验结果。"""
    allowed: bool
    exceeded: bool
    exceeded_dims: list[str]
    message: str = ""