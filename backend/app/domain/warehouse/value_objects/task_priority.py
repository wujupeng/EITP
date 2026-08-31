"""Task 优先级枚举。"""

from __future__ import annotations

from enum import Enum


class TaskPriority(str, Enum):
    """WMS 作业任务优先级。"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"