"""用户管理应用服务。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.identity.aggregates.user_aggregate import AccountStatus, UserAggregate
from app.domain.policy.aggregates.password_policy_aggregate import PasswordPolicyAggregate
from app.domain.policy.services.password_hasher import get_password_hasher
from app.domain.shared.entity import EntityId
from app.infrastructure.identity.user_repository import UserRepository
from app.infrastructure.policy.password_history_repository import PasswordHistoryRepository
from app.infrastructure.policy.password_policy_repository import PasswordPolicyRepository
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode


class UserAppSvc:
    """用户管理应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._hasher = get_password_hasher()
        self._policy_repo = PasswordPolicyRepository(session)
        self._history_repo = PasswordHistoryRepository(session)

    async def create_user(
        self,
        tenant_id: UUID,
        username: str,
        password: str,
        email: str | None = None,
        phone: str | None = None,
        real_name: str | None = None,
        is_tenant_admin: bool = False,
        is_platform_admin: bool = False,
    ) -> UserAggregate:
        """创建用户。"""
        existing = await self._user_repo.find_by_tenant_username(tenant_id, username)
        if existing is not None:
            raise IAMError(IAMErrorCode.USER_DUPLICATE, f"用户名已存在: {username}")

        policy = await self._policy_repo.get_tenant(tenant_id)
        if policy is None:
            policy = PasswordPolicyAggregate.tenant_default(tenant_id)

        policy.validate(password, username, email or "")

        hash_result = self._hasher.hash(password)
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)

        user = UserAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            username=username,
            password_hash=hash_result.hash,
            password_salt=hash_result.salt,
            email=email,
            phone=phone,
            real_name=real_name,
            account_status=AccountStatus.ACTIVE,
            password_changed_at=now,
            password_expires_at=now + timedelta(days=policy.expire_days),
            is_tenant_admin=is_tenant_admin,
            is_platform_admin=is_platform_admin,
        )

        await self._user_repo.save(user)
        await self._history_repo.add(user.id.value, hash_result.hash, hash_result.salt)
        await self._session.commit()
        return user

    async def list_users(self, tenant_id: UUID, offset: int = 0, limit: int = 50) -> list[UserAggregate]:
        return await self._user_repo.list_by_tenant(tenant_id, offset, limit)

    async def get_user(self, user_id: UUID) -> UserAggregate | None:
        return await self._user_repo.get_by_id(user_id)

    async def disable_user(self, user_id: UUID) -> UserAggregate:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise IAMError(IAMErrorCode.USER_NOT_FOUND, "用户不存在")
        user.disable()
        await self._user_repo.update(user)
        await self._session.commit()
        return user

    async def enable_user(self, user_id: UUID) -> UserAggregate:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise IAMError(IAMErrorCode.USER_NOT_FOUND, "用户不存在")
        user.enable()
        await self._user_repo.update(user)
        await self._session.commit()
        return user

    async def reset_password(self, user_id: UUID, new_password: str) -> None:
        """管理员重置密码。"""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise IAMError(IAMErrorCode.USER_NOT_FOUND, "用户不存在")

        policy = await self._policy_repo.get_tenant(user.tenant_id)
        if policy is None:
            policy = PasswordPolicyAggregate.tenant_default(user.tenant_id)

        policy.validate(new_password, user.username)

        hash_result = self._hasher.hash(new_password)
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)

        from app.infrastructure.identity.models import UserORM
        from sqlalchemy import select
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            orm.password_hash = hash_result.hash
            orm.password_salt = hash_result.salt
            orm.password_changed_at = now
            orm.password_expires_at = now + timedelta(days=policy.expire_days)

        await self._history_repo.add(user_id, hash_result.hash, hash_result.salt)
        await self._session.commit()