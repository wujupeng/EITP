"""作业设备类型枚举。"""

from __future__ import annotations

from enum import Enum


class EquipmentType(str, Enum):
    """作业设备类型。"""
    FORKLIFT = "forklift"
    PDA = "pda"
    SCANNER = "scanner"
    CONVEYOR = "conveyor"
    AGV = "agv"