"""空间层级无环校验服务 - DFS 检测有向无环树。"""

from __future__ import annotations

from uuid import UUID

from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class HierarchyCycleGuard:
    """层级循环引用校验服务 - 输入层级关系，检测是否含循环。

    核心逻辑：DFS 遍历有向图，检测是否存在回边（back edge）。
    若存在循环引用，拒绝并抛出 EITP_WMS_HIERARCHY_CYCLE。
    """

    @staticmethod
    def has_cycle(parent_map: dict[UUID, UUID | None]) -> bool:
        """检测层级关系中是否存在循环引用。

        Args:
            parent_map: 节点 ID → 父节点 ID 映射（None 表示根节点）

        Returns:
            True 如果存在循环，False 否则
        """
        for start_node in parent_map:
            visited: set[UUID] = set()
            current: UUID | None = start_node
            while current is not None and current in parent_map:
                if current in visited:
                    return True
                visited.add(current)
                current = parent_map[current]
        return False

    @staticmethod
    def validate(parent_map: dict[UUID, UUID | None]) -> None:
        """校验层级关系无循环，有循环则抛出异常。"""
        if HierarchyCycleGuard.has_cycle(parent_map):
            raise WMSError(
                WMSErrorCode.HIERARCHY_CYCLE,
                "空间层级关系存在循环引用",
                details={"node_count": len(parent_map)},
            )

    @staticmethod
    def validate_move(
        parent_map: dict[UUID, UUID | None],
        node_id: UUID,
        new_parent_id: UUID,
    ) -> None:
        """校验将 node_id 移动到 new_parent_id 下不会产生循环。

        即 new_parent_id 不能是 node_id 的后代。
        """
        if node_id == new_parent_id:
            raise WMSError(
                WMSErrorCode.HIERARCHY_CYCLE,
                "不能将节点移动到自身之下",
                details={"node_id": str(node_id)},
            )
        temp_map = dict(parent_map)
        temp_map[node_id] = new_parent_id
        HierarchyCycleGuard.validate(temp_map)