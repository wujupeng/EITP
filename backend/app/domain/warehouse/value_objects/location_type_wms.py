"""WMS 库位类型枚举 - 区别于 INV LocationType，描述物理存储形态。"""

from __future__ import annotations

from enum import Enum


class LocationTypeWms(str, Enum):
    """WMS 库位物理类型 - 描述库位的物理存储形态。"""
    FLOOR = "floor"
    SHELF = "shelf"
    COLD = "cold"
    FROZEN = "frozen"