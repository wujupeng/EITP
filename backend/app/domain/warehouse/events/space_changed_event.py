"""空间变更领域事件 - 仓库/库区/区域/库位等空间结构变更时发布。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.domain.shared.domain_event import DomainEvent


class SpaceEntityType(str, Enum):
    WAREHOUSE = "warehouse"
    ZONE = "zone"
    AREA = "area"
    LOCATION = "location"
    BIN = "bin"
    EQUIPMENT = "equipment"


class SpaceAction(str, Enum):
    CREATED = "created"
    ENABLED = "enabled"
    DISABLED = "disabled"
    UPDATED = "updated"
    MOVED = "moved"


@dataclass(frozen=True, kw_only=True)
class SpaceChangedEvent(DomainEvent):
    """空间变更事件 - 携带实体类型/ID/动作/前后状态。"""

    tenant_id: UUID
    entity_type: SpaceEntityType
    entity_id: UUID
    action: SpaceAction
    before_state: dict | None = None
    after_state: dict | None = None