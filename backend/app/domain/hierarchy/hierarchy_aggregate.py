"""层级聚合根 - 一致性边界入口，管理层级节点与领域事件。"""

from __future__ import annotations

from uuid import UUID

from app.domain.hierarchy.hierarchy_events import (
    HierarchyNodeCreatedEvent,
    HierarchyNodeDisabledEvent,
)
from app.domain.hierarchy.hierarchy_node import HierarchyLevel, HierarchyNode
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId


class HierarchyAggregate(AggregateRoot):
    """层级聚合根 - 管理一个租户内的层级树一致性。

    职责：
    - 创建层级节点（校验父级合法性、深度上限）
    - 停用层级节点（级联停用下级）
    - 收集领域事件
    """

    def __init__(self, id: EntityId, tenant_id: UUID) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._nodes: dict[UUID, HierarchyNode] = {}

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def nodes(self) -> dict[UUID, HierarchyNode]:
        return dict(self._nodes)

    def add_node(
        self,
        node: HierarchyNode,
        parent_depth: int = 0,
    ) -> None:
        """向聚合添加节点，校验深度上限并记录事件。

        Args:
            node: 待添加的层级节点
            parent_depth: 父节点的当前深度（根节点为 0）

        Raises:
            ValueError: 深度超过上限
        """
        new_depth = parent_depth + 1
        if new_depth > HierarchyLevel.max_depth():
            from app.interfaces.middleware.error_handler import (
                ErrorCode,
                HierarchyError,
            )
            raise HierarchyError(
                ErrorCode.HIERARCHY_DEPTH_EXCEEDED,
                f"层级深度 {new_depth} 超过上限 {HierarchyLevel.max_depth()}",
            )

        if node.tenant_id != self._tenant_id:
            from app.interfaces.middleware.error_handler import (
                ErrorCode,
                HierarchyError,
            )
            raise HierarchyError(
                ErrorCode.HIERARCHY_CROSS_TENANT,
                "节点 tenant_id 与聚合 tenant_id 不匹配，跨租户引用被拒绝",
            )

        self._nodes[node.id.value] = node
        self._record_event(
            HierarchyNodeCreatedEvent(
                tenant_id=self._tenant_id,
                node_id=node.id.value,
                level=node.level.value,
                parent_id=node.parent_id.value if node.parent_id else None,
            )
        )

    def disable_node(self, node_id: UUID) -> HierarchyNode | None:
        """停用指定节点并记录事件。

        Returns:
            被停用的节点，若不存在返回 None
        """
        node = self._nodes.get(node_id)
        if node is None:
            return None

        node.disable()
        self._record_event(
            HierarchyNodeDisabledEvent(
                tenant_id=self._tenant_id,
                node_id=node_id,
                level=node.level.value,
            )
        )
        return node

    def get_node(self, node_id: UUID) -> HierarchyNode | None:
        return self._nodes.get(node_id)

    def get_children(self, parent_id: UUID) -> list[HierarchyNode]:
        """获取指定父节点的直接子节点。"""
        return [
            n for n in self._nodes.values()
            if n.parent_id is not None and n.parent_id.value == parent_id
        ]