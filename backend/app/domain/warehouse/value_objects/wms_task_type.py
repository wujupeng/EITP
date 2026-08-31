"""WMS Task 类型枚举 - P0 包含 P1 作业类型枚举位预留。"""

from __future__ import annotations

from enum import Enum


class WmsTaskType(str, Enum):
    """WMS 作业任务类型 - P0 前 5 种，P1 后 3 种。"""
    RECEIVING = "receiving"
    PUTAWAY = "putaway"
    PICKING = "picking"
    TRANSFER = "transfer"
    SHIPPING = "shipping"
    PACKING = "packing"
    CYCLE_COUNT = "cycle_count"
    QC = "qc"