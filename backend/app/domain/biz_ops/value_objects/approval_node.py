"""ApprovalNode 值对象 - 审批节点配置。"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.domain.biz_ops.enums.enums import RoutingStrategyType, TimeoutStrategy


@dataclass(frozen=True)
class ApprovalNode:
    """审批节点 - 节点顺序、路由策略、审批操作、超时配置、会签配置。"""
    node_order: int
    node_name: str
    routing_strategy: RoutingStrategyType
    routing_config: dict = field(default_factory=dict)
    timeout_seconds: int = 86400
    timeout_strategy: TimeoutStrategy = TimeoutStrategy.WARN_ONLY
    is_countersign: bool = False
    countersign_ratio: float = 1.0
    condition_expression: str | None = None

    def is_last_node(self, total_nodes: int) -> bool:
        return self.node_order >= total_nodes