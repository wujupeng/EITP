"""RefreshTokenRepository - Refresh Token 持久化与轮换。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.authn.value_objects.tokens import RefreshTokenInfo


class RefreshTokenORM:
    """Refresh Token ORM - 使用原生 SQL 映射。"""

    __tablename__ = "iam_refresh_token"


class RefreshTokenRepository:
    """Refresh Token 仓储 - 轮换 + 滑动续期。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, token_info: RefreshTokenInfo) -> None:
        from sqlalchemy import text
        await self._session.execute(
            text(
                "INSERT INTO iam_refresh_token (id, user_id, tenant_id, token_hash, expires_at, is_revoked, created_at) "
                "VALUES (:id, :user_id, :tenant_id, :token_hash, :expires_at, false, NOW())"
            ),
            {
                "id": str(token_info.id),
                "user_id": str(token_info.user_id),
                "tenant_id": str(token_info.tenant_id),
                "token_hash": token_info.token_hash,
                "expires_at": token_info.expires_at,
            },
        )

    async def get_by_hash(self, token_hash: str) -> RefreshTokenInfo | None:
        from sqlalchemy import text
        result = await self._session.execute(
            text(
                "SELECT id, user_id, tenant_id, token_hash, expires_at, is_revoked, created_at, last_used_at "
                "FROM iam_refresh_token WHERE token_hash = :hash"
            ),
            {"hash": token_hash},
        )
        row = result.fetchone()
        if row is None:
            return None
        return RefreshTokenInfo(
            id=row[0],
            user_id=row[1],
            tenant_id=row[2],
            token_hash=row[3],
            expires_at=row[4],
            is_revoked=row[5],
            created_at=row[6],
            last_used_at=row[7],
        )

    async def revoke(self, token_id: UUID) -> None:
        from sqlalchemy import text
        await self._session.execute(
            text("UPDATE iam_refresh_token SET is_revoked = true WHERE id = :id"),
            {"id": str(token_id)},
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        from sqlalchemy import text
        await self._session.execute(
            text("UPDATE iam_refresh_token SET is_revoked = true WHERE user_id = :uid AND is_revoked = false"),
            {"uid": str(user_id)},
        )

    async def update_last_used(self, token_id: UUID) -> None:
        from sqlalchemy import text
        await self._session.execute(
            text("UPDATE iam_refresh_token SET last_used_at = NOW() WHERE id = :id"),
            {"id": str(token_id)},
        )