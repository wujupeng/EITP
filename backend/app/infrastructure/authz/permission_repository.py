"""PermissionRepository - 权限持久化。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.authz.entities.permission import Permission
from app.infrastructure.authz.models import PermissionORM, RolePermissionORM


class PermissionRepository:
    """权限仓储 - 全局共享，不按租户隔离。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        stmt = select(PermissionORM).where(PermissionORM.id == permission_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def get_by_code(self, code: str) -> Permission | None:
        stmt = select(PermissionORM).where(PermissionORM.code == code)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def list_all(self) -> list[Permission]:
        stmt = select(PermissionORM)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def list_by_module(self, module: str) -> list[Permission]:
        stmt = select(PermissionORM).where(PermissionORM.module == module)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def save(self, permission: Permission) -> Permission:
        orm = PermissionORM(
            id=permission.id,
            code=permission.code,
            name=permission.name,
            module=permission.module,
            description=permission.description,
        )
        self._session.add(orm)
        await self._session.flush()
        return permission

    async def get_codes_by_role_ids(self, role_ids: list[UUID]) -> set[str]:
        if not role_ids:
            return set()
        stmt = (
            select(PermissionORM.code)
            .join(RolePermissionORM, RolePermissionORM.permission_id == PermissionORM.id)
            .where(RolePermissionORM.role_id.in_(role_ids))
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    def _to_domain(self, orm: PermissionORM) -> Permission:
        return Permission(
            id=orm.id,
            code=orm.code,
            name=orm.name,
            module=orm.module,
            description=orm.description or "",
            created_at=orm.created_at,
        )