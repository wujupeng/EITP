"""物流信息值对象。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LogisticsInfo:
    """物流信息值对象 - 发货物流追踪。"""
    logistics_no: str = ""
    logistics_company: str = ""
    shipped_at: datetime | None = None

    def is_set(self) -> bool:
        return bool(self.logistics_no) and bool(self.logistics_company)