"""SAL 客户分类状态枚举。"""

from __future__ import annotations

from enum import Enum


class CategoryStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"