"""PasswordHistoryRepository - 密码历史持久化。"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.policy.models import PasswordHistoryORM


class PasswordHistoryRepository:
    """密码历史仓储 - 存储每用户最近 N 次历史密码哈希。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: UUID, password_hash: str, password_salt: str) -> None:
        orm = PasswordHistoryORM(
            id=uuid4(),
            user_id=user_id,
            password_hash=password_hash,
            password_salt=password_salt,
        )
        self._session.add(orm)
        await self._session.flush()

    async def get_recent(self, user_id: UUID, count: int) -> list[PasswordHistoryORM]:
        stmt = (
            select(PasswordHistoryORM)
            .where(PasswordHistoryORM.user_id == user_id)
            .order_by(PasswordHistoryORM.created_at.desc())
            .limit(count)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def is_reused(self, user_id: UUID, new_hash: str, count: int = 5) -> bool:
        histories = await self.get_recent(user_id, count)
        for h in histories:
            if h.password_hash == new_hash:
                return True
        return False

    async def prune_old(self, user_id: UUID, keep_count: int) -> None:
        histories = await self.get_recent(user_id, keep_count + 100)
        if len(histories) <= keep_count:
            return
        to_delete = histories[keep_count:]
        for h in to_delete:
            await self._session.delete(h)
        await self._session.flush()