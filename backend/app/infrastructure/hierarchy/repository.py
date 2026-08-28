"""HierarchyRepository - 闭包表持久化与祖先链维护。"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.hierarchy.hierarchy_node import HierarchyLevel, HierarchyNode
from app.domain.shared.entity import EntityId
from app.infrastructure.hierarchy.models import HierarchyClosureORM, HierarchyNodeORM


class HierarchyRepository:
    """层级仓储 - 管理节点与闭包表持久化。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, node_id: UUID, tenant_id: UUID) -> HierarchyNode | None:
        """按 ID 获取节点（租户隔离）。"""
        stmt = select(HierarchyNodeORM).where(
            HierarchyNodeORM.id == node_id,
            HierarchyNodeORM.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def save(
        self,
        node: HierarchyNode,
        parent_id: UUID | None = None,
    ) -> HierarchyNode:
        """保存节点并维护闭包表祖先链。"""
        orm = HierarchyNodeORM(
            id=node.id.value,
            tenant_id=node.tenant_id,
            level=node.level.value,
            name=node.name,
            parent_id=node.parent_id.value if node.parent_id else None,
            is_active=node.is_active,
        )
        self._session.add(orm)
        await self._session.flush()

        await self._insert_closure(node.id.value, parent_id, node.tenant_id)

        return node

    async def _insert_closure(
        self,
        node_id: UUID,
        parent_id: UUID | None,
        tenant_id: UUID,
    ) -> None:
        """插入闭包表记录：自引用 + 继承父节点的祖先链。"""
        self._session.add(HierarchyClosureORM(
            ancestor_id=node_id,
            descendant_id=node_id,
            depth=0,
            tenant_id=tenant_id,
        ))

        if parent_id is not None:
            await self._session.flush()
            inherit_sql = text(
                """
                INSERT INTO hierarchy_closure (ancestor_id, descendant_id, depth, tenant_id)
                SELECT ancestor_id, :node_id, depth + 1, :tenant_id
                FROM hierarchy_closure
                WHERE descendant_id = :parent_id AND tenant_id = :tenant_id
                """
            )
            await self._session.execute(
                inherit_sql,
                {"node_id": node_id, "parent_id": parent_id, "tenant_id": tenant_id},
            )

    async def get_ancestors(self, node_id: UUID, tenant_id: UUID) -> list[HierarchyNode]:
        """获取节点的所有祖先（从根到父级）。"""
        sql = text(
            """
            SELECT n.* FROM hierarchy_node n
            JOIN hierarchy_closure c ON c.ancestor_id = n.id
            WHERE c.descendant_id = :node_id AND c.depth > 0 AND n.tenant_id = :tenant_id
            ORDER BY c.depth DESC
            """
        )
        result = await self._session.execute(sql, {"node_id": node_id, "tenant_id": tenant_id})
        rows = result.fetchall()
        return [self._row_to_domain(row) for row in rows]

    async def get_descendants(self, node_id: UUID, tenant_id: UUID) -> list[HierarchyNode]:
        """获取节点的所有后代。"""
        sql = text(
            """
            SELECT n.* FROM hierarchy_node n
            JOIN hierarchy_closure c ON c.descendant_id = n.id
            WHERE c.ancestor_id = :node_id AND c.depth > 0 AND n.tenant_id = :tenant_id
            ORDER BY c.depth ASC
            """
        )
        result = await self._session.execute(sql, {"node_id": node_id, "tenant_id": tenant_id})
        rows = result.fetchall()
        return [self._row_to_domain(row) for row in rows]

    async def get_children(self, parent_id: UUID, tenant_id: UUID) -> list[HierarchyNode]:
        """获取直接子节点。"""
        stmt = select(HierarchyNodeORM).where(
            HierarchyNodeORM.parent_id == parent_id,
            HierarchyNodeORM.tenant_id == tenant_id,
            HierarchyNodeORM.is_active == True,  # noqa: E712
        ).order_by(HierarchyNodeORM.name)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars()]

    async def update_active_status(
        self,
        node_id: UUID,
        is_active: bool,
        tenant_id: UUID,
    ) -> None:
        """更新节点活跃状态。"""
        sql = text(
            """
            UPDATE hierarchy_node SET is_active = :is_active, updated_at = NOW()
            WHERE id = :node_id AND tenant_id = :tenant_id
            """
        )
        await self._session.execute(
            sql,
            {"node_id": node_id, "is_active": is_active, "tenant_id": tenant_id},
        )

    @staticmethod
    def _to_domain(orm: HierarchyNodeORM) -> HierarchyNode:
        return HierarchyNode(
            id=EntityId(orm.id),
            tenant_id=orm.tenant_id,
            level=HierarchyLevel(orm.level),
            name=orm.name,
            parent_id=EntityId(orm.parent_id) if orm.parent_id else None,
            is_active=orm.is_active,
        )

    @staticmethod
    def _row_to_domain(row) -> HierarchyNode:  # type: ignore[no-untyped-def]
        return HierarchyNode(
            id=EntityId(row.id),
            tenant_id=row.tenant_id,
            level=HierarchyLevel(row.level),
            name=row.name,
            parent_id=EntityId(row.parent_id) if row.parent_id else None,
            is_active=row.is_active,
        )