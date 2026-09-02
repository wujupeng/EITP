"""IVerifier 统一接口 - 16 项验证器实现此接口。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from app.domain.prod.engine.enums import (
    VerificationConclusion,
    VerificationItem,
)


@dataclass(frozen=True)
class VerificationConfig:
    """验证执行配置。"""

    verification_item: VerificationItem
    tenant_id: UUID
    environment: str
    parameters: dict[str, Any] = field(default_factory=dict)
    metrics_promql: str | None = None
    metrics_time_window: tuple[float, float] | None = None


@dataclass(frozen=True)
class VerificationResult:
    """验证执行结果。"""

    conclusion: VerificationConclusion
    report: dict[str, Any]
    failure_code: str | None = None
    failure_detail: dict | None = None
    duration_ms: int = 0
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class IVerifier(Protocol):
    """验证器统一接口。"""

    @property
    def item(self) -> VerificationItem: ...

    async def execute(self, config: VerificationConfig) -> VerificationResult: ...