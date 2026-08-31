"""UserRepository - 用户持久化与租户内唯一性校验。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.identity.aggregates.user_aggregate import AccountStatus, UserAggregate
from app.domain.shared.entity import EntityId
from app.infrastructure.identity.models import UserORM
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode


class UserRepository:
    """用户仓储 - 通过 tenant_id 自动隔离，PII 字段加密存储。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> UserAggregate | None:
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def find_by_tenant_username(self, tenant_id: UUID, username: str) -> UserAggregate | None:
        stmt = select(UserORM).where(
            UserORM.tenant_id == tenant_id,
            UserORM.username == username,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def save(self, user: UserAggregate) -> UserAggregate:
        existing = await self.get_by_id(user.id.value)
        if existing is not None:
            raise IAMError(
                IAMErrorCode.USER_DUPLICATE,
                f"用户已存在: {user.username}",
            )

        orm = self._to_orm(user)
        self._session.add(orm)
        await self._session.flush()
        return user

    async def update(self, user: UserAggregate) -> UserAggregate:
        stmt = select(UserORM).where(UserORM.id == user.id.value)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise IAMError(
                IAMErrorCode.USER_NOT_FOUND,
                f"用户不存在: {user.username}",
            )

        orm.password_hash = user.password_hash
        orm.password_salt = user.password_salt
        orm.account_status = user.account_status.value
        orm.failed_login_count = user.failed_login_count
        orm.locked_until = user.locked_until
        orm.password_changed_at = user.password_changed_at
        orm.password_expires_at = user.password_expires_at
        orm.last_login_at = user.last_login_at
        orm.last_login_ip = user.last_login_ip
        await self._session.flush()
        return user

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[UserAggregate]:
        stmt = (
            select(UserORM)
            .where(UserORM.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    def _to_domain(self, orm: UserORM) -> UserAggregate:
        return UserAggregate(
            id=EntityId(orm.id),
            tenant_id=orm.tenant_id,
            username=orm.username,
            password_hash=orm.password_hash,
            password_salt=orm.password_salt,
            email=orm.email_encrypted,
            phone=orm.phone_encrypted,
            real_name=orm.real_name_encrypted,
            account_status=AccountStatus(orm.account_status),
            failed_login_count=orm.failed_login_count,
            locked_until=orm.locked_until,
            password_changed_at=orm.password_changed_at,
            password_expires_at=orm.password_expires_at,
            last_login_at=orm.last_login_at,
            last_login_ip=orm.last_login_ip,
            is_platform_admin=orm.is_platform_admin,
            is_tenant_admin=orm.is_tenant_admin,
        )

    def _to_orm(self, user: UserAggregate) -> UserORM:
        return UserORM(
            id=user.id.value,
            tenant_id=user.tenant_id,
            username=user.username,
            email_encrypted=user.email,
            phone_encrypted=user.phone,
            real_name_encrypted=user.real_name,
            password_hash=user.password_hash,
            password_salt=user.password_salt,
            account_status=user.account_status.value,
            failed_login_count=user.failed_login_count,
            locked_until=user.locked_until,
            password_changed_at=user.password_changed_at,
            password_expires_at=user.password_expires_at,
            last_login_at=user.last_login_at,
            last_login_ip=user.last_login_ip,
            is_platform_admin=user.is_platform_admin,
            is_tenant_admin=user.is_tenant_admin,
        )