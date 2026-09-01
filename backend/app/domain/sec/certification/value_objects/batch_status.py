"""BatchStatus 枚举 - 认证批次状态。"""

from __future__ import annotations

from enum import Enum


class BatchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"