"""PasswordPolicyRepository - 密码策略持久化。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.policy.aggregates.password_policy_aggregate import (
    PasswordPolicyAggregate,
    PolicyScope,
)
from app.infrastructure.policy.models import PasswordPolicyORM


class PasswordPolicyRepository:
    """密码策略仓储 - 平台级/租户级隔离。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_platform(self) -> PasswordPolicyAggregate | None:
        stmt = select(PasswordPolicyORM).where(
            PasswordPolicyORM.scope_level == PolicyScope.PLATFORM.value
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def get_tenant(self, tenant_id: UUID) -> PasswordPolicyAggregate | None:
        stmt = select(PasswordPolicyORM).where(
            PasswordPolicyORM.scope_level == PolicyScope.TENANT.value,
            PasswordPolicyORM.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def save(self, policy: PasswordPolicyAggregate) -> PasswordPolicyAggregate:
        orm = PasswordPolicyORM(
            id=policy.id,
            scope_level=policy.scope_level.value,
            tenant_id=policy.tenant_id,
            min_length=policy.min_length,
            required_char_categories=policy.required_char_categories,
            history_count=policy.history_count,
            expire_days=policy.expire_days,
            expire_grace_days=policy.expire_grace_days,
            max_login_attempts=policy.max_login_attempts,
            lockout_duration_minutes=policy.lockout_duration_minutes,
            ip_ban_threshold=policy.ip_ban_threshold,
            ip_ban_duration_minutes=policy.ip_ban_duration_minutes,
        )
        self._session.add(orm)
        await self._session.flush()
        return policy

    async def update(self, policy: PasswordPolicyAggregate) -> PasswordPolicyAggregate:
        stmt = select(PasswordPolicyORM).where(PasswordPolicyORM.id == policy.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return await self.save(policy)
        orm.min_length = policy.min_length
        orm.required_char_categories = policy.required_char_categories
        orm.history_count = policy.history_count
        orm.expire_days = policy.expire_days
        orm.expire_grace_days = policy.expire_grace_days
        orm.max_login_attempts = policy.max_login_attempts
        orm.lockout_duration_minutes = policy.lockout_duration_minutes
        orm.ip_ban_threshold = policy.ip_ban_threshold
        orm.ip_ban_duration_minutes = policy.ip_ban_duration_minutes
        await self._session.flush()
        return policy

    def _to_domain(self, orm: PasswordPolicyORM) -> PasswordPolicyAggregate:
        return PasswordPolicyAggregate(
            id=orm.id,
            scope_level=PolicyScope(orm.scope_level),
            tenant_id=orm.tenant_id,
            min_length=orm.min_length,
            required_char_categories=orm.required_char_categories,
            history_count=orm.history_count,
            expire_days=orm.expire_days,
            expire_grace_days=orm.expire_grace_days,
            max_login_attempts=orm.max_login_attempts,
            lockout_duration_minutes=orm.lockout_duration_minutes,
            ip_ban_threshold=orm.ip_ban_threshold,
            ip_ban_duration_minutes=orm.ip_ban_duration_minutes,
        )