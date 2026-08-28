"""层级校验领域服务 - 父级合法性、循环引用检测、跨租户引用拒绝。"""

from __future__ import annotations

from uuid import UUID

from app.domain.hierarchy.hierarchy_node import HierarchyLevel, HierarchyNode
from app.interfaces.middleware.error_handler import ErrorCode, HierarchyError


class HierarchyValidator:
    """层级校验领域服务。"""

    @staticmethod
    def validate_parent(
        node_level: HierarchyLevel,
        parent: HierarchyNode | None,
        tenant_id: UUID,
    ) -> None:
        """校验父级合法性。

        Rules:
        - C-HIER-01: 跨租户引用拒绝
        - 父级层级必须比子节点高一级
        - 根节点（PLATFORM）无父级
        """
        if node_level == HierarchyLevel.PLATFORM:
            if parent is not None:
                raise HierarchyError(
                    ErrorCode.HIERARCHY_CROSS_TENANT,
                    "PLATFORM 层级节点不能有父级",
                )
            return

        if parent is None:
            raise HierarchyError(
                ErrorCode.HIERARCHY_CROSS_TENANT,
                f"{node_level.name} 层级节点必须有父级",
            )

        if parent.tenant_id != tenant_id:
            raise HierarchyError(
                ErrorCode.HIERARCHY_CROSS_TENANT,
                "父节点属于不同租户，跨租户引用被拒绝",
            )

        expected_parent_level = HierarchyLevel(node_level.value - 1)
        if parent.level != expected_parent_level:
            raise HierarchyError(
                ErrorCode.HIERARCHY_CROSS_TENANT,
                f"父节点层级应为 {expected_parent_level.name}，实际为 {parent.level.name}",
            )

    @staticmethod
    def validate_no_circular_ref(
        node_id: UUID,
        new_parent_id: UUID,
        ancestor_chain: dict[UUID, UUID | None],
    ) -> None:
        """检测循环引用（C-HIER-02）。

        Args:
            node_id: 待移动节点 ID
            new_parent_id: 新父节点 ID
            ancestor_chain: 节点 ID → 父节点 ID 的映射

        Raises:
            HierarchyError: 若新父节点是当前节点的后代
        """
        current = new_parent_id
        visited: set[UUID] = set()

        while current is not None:
            if current == node_id:
                raise HierarchyError(
                    ErrorCode.HIERARCHY_CIRCULAR_REF,
                    "检测到循环引用：新父节点是当前节点的后代",
                )
            if current in visited:
                raise HierarchyError(
                    ErrorCode.HIERARCHY_CIRCULAR_REF,
                    "检测到祖先链中存在循环",
                )
            visited.add(current)
            current = ancestor_chain.get(current)

    @staticmethod
    def validate_depth(current_depth: int) -> None:
        """校验深度上限（≤7）。"""
        if current_depth > HierarchyLevel.max_depth():
            raise HierarchyError(
                ErrorCode.HIERARCHY_DEPTH_EXCEEDED,
                f"层级深度 {current_depth} 超过上限 {HierarchyLevel.max_depth()}",
            )