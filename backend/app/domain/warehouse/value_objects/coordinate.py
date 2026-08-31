"""坐标值对象 - P1 路径优化使用，P0 预留可空。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinate:
    """三维坐标值对象 - x/y/z，P1 路径优化使用，P0 预留可空。"""

    x: float | None = None
    y: float | None = None
    z: float | None = None

    def is_set(self) -> bool:
        """坐标是否已设置（非全 None）。"""
        return self.x is not None or self.y is not None or self.z is not None

    def distance_to(self, other: Coordinate) -> float | None:
        """计算到另一个坐标的欧氏距离，任一坐标未设置则返回 None。"""
        if not self.is_set() or not other.is_set():
            return None
        dx = (self.x or 0) - (other.x or 0)
        dy = (self.y or 0) - (other.y or 0)
        dz = (self.z or 0) - (other.z or 0)
        return (dx * dx + dy * dy + dz * dz) ** 0.5