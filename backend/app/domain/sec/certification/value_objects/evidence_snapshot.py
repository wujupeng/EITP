"""EvidenceSnapshot 值对象 - 认证证据快照，不可变。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class EvidenceSnapshot:
    request_log: dict[str, Any] = field(default_factory=dict)
    response_log: dict[str, Any] = field(default_factory=dict)
    sql_plan: str = ""
    rls_hits: list[dict[str, Any]] = field(default_factory=list)
    redis_keys: list[str] = field(default_factory=list)
    audit_records: list[dict[str, Any]] = field(default_factory=list)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def verify_completeness(self) -> bool:
        if not self.request_log:
            return False
        if not self.response_log:
            return False
        return True