"""Repository 接口 - 领域层定义的持久化抽象。"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from app.domain.shared.entity import Entity, EntityId

TEntity = TypeVar("TEntity", bound=Entity)


@runtime_checkable
class Repository(Protocol[TEntity]):
    """Repository 协议 - 异步持久化抽象。"""

    async def get_by_id(self, id: EntityId) -> TEntity | None: ...

    async def save(self, entity: TEntity) -> TEntity: ...

    async def remove(self, entity: TEntity) -> None: ...