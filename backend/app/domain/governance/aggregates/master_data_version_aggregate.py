"""主数据版本聚合根 - 版本不可变约束（append-only）。

写入后不可修改不可删除（spec 4.2.1，REVOKE UPDATE/DELETE + Trigger 双保险）。
版本号从 1 递增。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class ChangeType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DISABLE = "disable"
    ENABLE = "enable"
    PUBLISH = "publish"
    ROLLBACK = "rollback"


class MasterDataVersionAggregate(AggregateRoot):
    """主数据版本聚合根 - 不可变，append-only。

    snapshot_before 首次创建时为空，后续版本含前一版本快照。
    """

    def __init__(
        self,
        id: EntityId,
        entity_type: str,
        entity_id: UUID,
        version_number: int,
        snapshot_after: dict,
        change_type: ChangeType,
        operated_by: UUID,
        tenant_id: UUID | None = None,
        snapshot_before: dict | None = None,
        reason: str | None = None,
        operated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        if version_number < 1:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                "版本号必须从 1 开始递增",
            )
        self._tenant_id = tenant_id
        self._entity_type = entity_type
        self._entity_id = entity_id
        self._version_number = version_number
        self._snapshot_before = snapshot_before
        self._snapshot_after = snapshot_after
        self._change_type = change_type
        self._operated_by = operated_by
        self._reason = reason
        self._operated_at = operated_at or datetime.now(timezone.utc)

    @property
    def tenant_id(self) -> UUID | None:
        return self._tenant_id

    @property
    def entity_type(self) -> str:
        return self._entity_type

    @property
    def entity_id(self) -> UUID:
        return self._entity_id

    @property
    def version_number(self) -> int:
        return self._version_number

    @property
    def snapshot_before(self) -> dict | None:
        return self._snapshot_before

    @property
    def snapshot_after(self) -> dict:
        return self._snapshot_after

    @property
    def change_type(self) -> ChangeType:
        return self._change_type

    @property
    def operated_by(self) -> UUID:
        return self._operated_by

    @property
    def reason(self) -> str | None:
        return self._reason

    @property
    def operated_at(self) -> datetime:
        return self._operated_at

    def is_group_level(self) -> bool:
        return self._tenant_id is None

    @classmethod
    def create_initial(
        cls,
        entity_type: str,
        entity_id: UUID,
        snapshot_after: dict,
        operated_by: UUID,
        tenant_id: UUID | None = None,
        reason: str | None = None,
    ) -> MasterDataVersionAggregate:
        """创建初始版本（version_number=1，snapshot_before 为空）。"""
        return cls(
            id=EntityId.generate(),
            entity_type=entity_type,
            entity_id=entity_id,
            version_number=1,
            snapshot_after=snapshot_after,
            change_type=ChangeType.CREATE,
            operated_by=operated_by,
            tenant_id=tenant_id,
            snapshot_before=None,
            reason=reason,
        )

    @classmethod
    def create_update(
        cls,
        entity_type: str,
        entity_id: UUID,
        version_number: int,
        snapshot_before: dict,
        snapshot_after: dict,
        operated_by: UUID,
        tenant_id: UUID | None = None,
        reason: str | None = None,
    ) -> MasterDataVersionAggregate:
        """创建更新版本。"""
        return cls(
            id=EntityId.generate(),
            entity_type=entity_type,
            entity_id=entity_id,
            version_number=version_number,
            snapshot_after=snapshot_after,
            change_type=ChangeType.UPDATE,
            operated_by=operated_by,
            tenant_id=tenant_id,
            snapshot_before=snapshot_before,
            reason=reason,
        )