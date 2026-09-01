"""ApprovalStatus 枚举 - 平台管理员访问申请审批状态。"""

from __future__ import annotations

from enum import Enum


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    GRANTED = "granted"
    EXPIRED = "expired"