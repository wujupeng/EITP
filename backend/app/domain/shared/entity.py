"""实体基类 - 具有唯一标识的领域对象。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class EntityId:
    """实体标识 - UUID 值对象。"""

    value: UUID

    @classmethod
    def generate(cls) -> EntityId:
        return cls(value=uuid4())

    def __str__(self) -> str:
        return str(self.value)


class Entity:
    """实体基类 - 具有唯一标识与生命周期时间戳。"""

    def __init__(self, id: EntityId) -> None:
        self._id = id
        self._created_at = datetime.now(timezone.utc)
        self._updated_at = datetime.now(timezone.utc)

    @property
    def id(self) -> EntityId:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def _touch(self) -> None:
        self._updated_at = datetime.now(timezone.utc)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return type(self) is type(other) and self._id == other._id

    def __hash__(self) -> int:
        return hash((type(self), self._id))