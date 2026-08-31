"""WMS Task 状态枚举。"""

from __future__ import annotations

from enum import Enum


class WmsTaskStatus(str, Enum):
    """WMS 作业任务状态 - 六态状态机。"""
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"