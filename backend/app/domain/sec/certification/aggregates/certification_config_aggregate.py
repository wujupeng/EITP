"""CertificationConfigAggregate 聚合根 - 认证配置。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import SECError, SECErrorCode


@dataclass
class CertificationConfigAggregate:
    config_id: UUID = field(default_factory=uuid4)
    matrix_layers: list[str] = field(default_factory=lambda: [l.value for l in __import__("app.domain.sec.certification.value_objects.isolation_layer", fromlist=["IsolationLayer"]).IsolationLayer])
    strict_mode: bool = True
    alert_channels: list[str] = field(default_factory=lambda: ["email", "webhook"])
    report_retention_days: int = 365
    item_skip_reasons: dict[str, str] = field(default_factory=dict)
    tenant_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.updated_at = datetime.now(timezone.utc)

    def skip_item(self, item_id: str, reason: str) -> None:
        if not reason:
            raise SECError(SECErrorCode.SKIP_REASON_REQUIRED, f"Skip reason required for item {item_id}")
        self.item_skip_reasons[item_id] = reason
        self.updated_at = datetime.now(timezone.utc)

    def is_skipped(self, item_id: str) -> bool:
        return item_id in self.item_skip_reasons