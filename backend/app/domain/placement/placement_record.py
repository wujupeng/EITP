"""放置记录值对象 - 租户数据放置模式与连接目标。

spec 5.7 / design 2.2.2.7。
三种放置模式：shared_db / dedicated_db / dedicated_instance。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID


class PlacementType(str, Enum):
    """数据放置模式。"""

    SHARED_DB = "shared_db"
    DEDICATED_DB = "dedicated_db"
    DEDICATED_INSTANCE = "dedicated_instance"

    @property
    def isolation_strength(self) -> int:
        """隔离强度 - 值越大隔离越强。"""
        return {
            PlacementType.SHARED_DB: 1,
            PlacementType.DEDICATED_DB: 2,
            PlacementType.DEDICATED_INSTANCE: 3,
        }[self]


@dataclass(frozen=True)
class PlacementRecord:
    """放置记录 - 租户的数据放置模式与连接目标。

    spec 5.7.1 规则 5：独立数据库/实例模式的隔离强度高于共享模式。
    """

    tenant_id: UUID
    placement: PlacementType
    connection_target: str
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        placement: PlacementType,
        connection_target: str | None = None,
    ) -> PlacementRecord:
        target = connection_target or cls._default_target(placement, tenant_id)
        return cls(
            tenant_id=tenant_id,
            placement=placement,
            connection_target=target,
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _default_target(placement: PlacementType, tenant_id: UUID) -> str:
        if placement == PlacementType.SHARED_DB:
            return "shared-db-default"
        if placement == PlacementType.DEDICATED_DB:
            return f"dedicated-db-{tenant_id}"
        return f"dedicated-instance-{tenant_id}"

    def with_placement(self, placement: PlacementType) -> PlacementRecord:
        """切换放置模式，返回新实例。"""
        return PlacementRecord.create(
            tenant_id=self.tenant_id,
            placement=placement,
        )