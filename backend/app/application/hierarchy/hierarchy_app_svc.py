"""HierarchyAppSvc - 层级应用服务，编排领域层与仓储层。"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.hierarchy.hierarchy_aggregate import HierarchyAggregate
from app.domain.hierarchy.hierarchy_node import HierarchyLevel, HierarchyNode
from app.domain.hierarchy.hierarchy_validator import HierarchyValidator
from app.domain.shared.entity import EntityId
from app.infrastructure.hierarchy.repository import HierarchyRepository
from app.interfaces.middleware.tenant_context import TenantContext


class HierarchyAppSvc:
    """层级应用服务 - 提供节点 CRUD、层级树查询、级联停用。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = HierarchyRepository(session)

    async def create_node(
        self,
        level: HierarchyLevel,
        name: str,
        parent_id: UUID | None = None,
    ) -> HierarchyNode:
        """创建层级节点。"""
        ctx = TenantContext.current()
        if ctx is None:
            raise RuntimeError("无租户上下文")

        tenant_id = ctx.tenant_id
        parent: HierarchyNode | None = None
        parent_depth = 0

        if parent_id is not None:
            parent = await self._repo.get_by_id(parent_id, tenant_id)
            if parent is None:
                raise ValueError("父节点不存在")
            ancestors = await self._repo.get_ancestors(parent_id, tenant_id)
            parent_depth = len(ancestors) + 1

        HierarchyValidator.validate_parent(level, parent, tenant_id)
        HierarchyValidator.validate_depth(parent_depth + 1)

        node_id = EntityId.generate()
        node = HierarchyNode(
            id=node_id,
            tenant_id=tenant_id,
            level=level,
            name=name,
            parent_id=EntityId(parent_id) if parent_id else None,
        )

        aggregate = HierarchyAggregate(EntityId(uuid4()), tenant_id)
        aggregate.add_node(node, parent_depth)
        await self._repo.save(node, parent_id)
        await self._session.commit()

        return node

    async def get_node(self, node_id: UUID) -> HierarchyNode | None:
        """查询单个节点。"""
        ctx = TenantContext.current()
        if ctx is None:
            raise RuntimeError("无租户上下文")
        return await self._repo.get_by_id(node_id, ctx.tenant_id)

    async def get_tree(self, root_id: UUID | None = None) -> list[HierarchyNode]:
        """查询层级树。"""
        ctx = TenantContext.current()
        if ctx is None:
            raise RuntimeError("无租户上下文")

        if root_id is not None:
            return await self._repo.get_descendants(root_id, ctx.tenant_id)
        from sqlalchemy import select
        from app.infrastructure.hierarchy.models import HierarchyNodeORM

        stmt = select(HierarchyNodeORM).where(
            HierarchyNodeORM.tenant_id == ctx.tenant_id,
            HierarchyNodeORM.is_active == True,  # noqa: E712
        ).order_by(HierarchyNodeORM.level, HierarchyNodeORM.name)
        result = await self._session.execute(stmt)
        return [
            HierarchyNode(
                id=EntityId(orm.id),
                tenant_id=orm.tenant_id,
                level=HierarchyLevel(orm.level),
                name=orm.name,
                parent_id=EntityId(orm.parent_id) if orm.parent_id else None,
                is_active=orm.is_active,
            )
            for orm in result.scalars()
        ]

    async def disable_node(self, node_id: UUID) -> HierarchyNode | None:
        """停用节点并级联停用下级。"""
        ctx = TenantContext.current()
        if ctx is None:
            raise RuntimeError("无租户上下文")

        tenant_id = ctx.tenant_id
        node = await self._repo.get_by_id(node_id, tenant_id)
        if node is None:
            return None

        descendants = await self._repo.get_descendants(node_id, tenant_id)
        await self._repo.update_active_status(node_id, False, tenant_id)
        for desc in descendants:
            await self._repo.update_active_status(desc.id.value, False, tenant_id)

        await self._session.commit()
        node.disable()
        return node