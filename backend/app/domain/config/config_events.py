"""配置领域事件。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ConfigChangedEvent(DomainEvent):
    """配置变更事件 - 记录前后值与操作人。"""

    tenant_id: UUID
    config_key: str
    old_value: Any
    new_value: Any
    changed_by: UUID | None


@dataclass(frozen=True, kw_only=True)
class FeatureFlagChangedEvent(DomainEvent):
    """功能开关变更事件。"""

    tenant_id: UUID
    feature_key: str
    old_enabled: bool
    new_enabled: bool