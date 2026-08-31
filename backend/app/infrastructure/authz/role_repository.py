"""RoleRepository - 角色持久化与权限关联。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.authz.aggregates.role_aggregate import RoleAggregate
from app.infrastructure.authz.models import RoleORM, RolePermissionORM, UserRoleORM


class RoleRepository:
    """角色仓储。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, role_id: UUID) -> RoleAggregate | None:
        stmt = select(RoleORM).where(RoleORM.id == role_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        perms = await self._get_permission_ids(role_id)
        return self._to_domain(orm, perms)

    async def get_by_code(self, tenant_id: UUID, role_code: str) -> RoleAggregate | None:
        stmt = select(RoleORM).where(
            RoleORM.tenant_id == tenant_id,
            RoleORM.role_code == role_code,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        perms = await self._get_permission_ids(orm.id)
        return self._to_domain(orm, perms)

    async def list_by_tenant(self, tenant_id: UUID) -> list[RoleAggregate]:
        stmt = select(RoleORM).where(RoleORM.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        roles = []
        for orm in orms:
            perms = await self._get_permission_ids(orm.id)
            roles.append(self._to_domain(orm, perms))
        return roles

    async def save(self, role: RoleAggregate) -> RoleAggregate:
        orm = RoleORM(
            id=role.id,
            tenant_id=role.tenant_id,
            role_code=role.role_code,
            role_name=role.role_name,
            description=role.description,
            is_builtin=role.is_builtin,
            is_active=role.is_active,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._sync_permissions(role.id, role.permission_ids)
        return role

    async def update(self, role: RoleAggregate) -> RoleAggregate:
        stmt = select(RoleORM).where(RoleORM.id == role.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return await self.save(role)
        orm.role_name = role.role_name
        orm.description = role.description
        orm.is_active = role.is_active
        await self._session.flush()
        await self._sync_permissions(role.id, role.permission_ids)
        return role

    async def assign_to_user(self, user_id: UUID, role_id: UUID) -> None:
        stmt = insert(UserRoleORM).values(user_id=user_id, role_id=role_id).on_conflict_do_nothing()
        await self._session.execute(stmt)
        await self._session.flush()

    async def remove_from_user(self, user_id: UUID, role_id: UUID) -> None:
        stmt = delete(UserRoleORM).where(
            UserRoleORM.user_id == user_id,
            UserRoleORM.role_id == role_id,
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_user_role_ids(self, user_id: UUID) -> list[UUID]:
        stmt = select(UserRoleORM.role_id).where(UserRoleORM.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _get_permission_ids(self, role_id: UUID) -> set[UUID]:
        stmt = select(RolePermissionORM.permission_id).where(RolePermissionORM.role_id == role_id)
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def _sync_permissions(self, role_id: UUID, permission_ids: set[UUID]) -> None:
        await self._session.execute(
            delete(RolePermissionORM).where(RolePermissionORM.role_id == role_id)
        )
        for pid in permission_ids:
            await self._session.execute(
                insert(RolePermissionORM).values(role_id=role_id, permission_id=pid)
            )
        await self._session.flush()

    def _to_domain(self, orm: RoleORM, perms: set[UUID]) -> RoleAggregate:
        return RoleAggregate(
            id=orm.id,
            tenant_id=orm.tenant_id,
            role_code=orm.role_code,
            role_name=orm.role_name,
            description=orm.description or "",
            is_builtin=orm.is_builtin,
            is_active=orm.is_active,
            permission_ids=perms,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )