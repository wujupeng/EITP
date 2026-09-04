"""ApprovalOrchestrator - 审批流编排领域服务。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.biz_ops.aggregates.approval_flow_aggregate import ApprovalFlowAggregate
from app.domain.biz_ops.enums.enums import TimeoutStrategy
from app.domain.biz_ops.services.approver_routing import get_routing_strategy
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class ApprovalRecord:
    """审批记录 - append-only。"""

    def __init__(
        self,
        approval_id: UUID,
        node_order: int,
        action: str,
        operator_id: UUID,
        comment: str = "",
        timestamp: datetime | None = None,
    ):
        self.approval_id = approval_id
        self.node_order = node_order
        self.action = action
        self.operator_id = operator_id
        self.comment = comment
        self.timestamp = timestamp or datetime.now(timezone.utc)


class ApprovalOrchestrator:
    """审批流编排领域服务 - 多节点流转编排。

    复用 GovernanceWorkflowAggregate 状态机作为单节点执行引擎（每节点一个实例）。
    """

    def advance(
        self,
        flow: ApprovalFlowAggregate,
        current_node_order: int,
        action: str,
        operator_id: UUID,
        context: dict,
        comment: str = "",
    ) -> dict:
        """推进审批流 - 返回下一节点或完成。"""
        node = flow._find_node(current_node_order)
        if node is None:
            raise BizOpsError(BizOpsErrorCode.FLOW_NODE_INVALID, f"节点不存在: {current_node_order}")

        if action == "approve":
            next_order = current_node_order + 1
            if next_order > len(flow.nodes):
                return {"status": "approved", "next_node": None, "is_final": True}
            return {"status": "advancing", "next_node": next_order, "is_final": False}

        elif action == "reject":
            return {"status": "rejected", "next_node": None, "is_final": True}

        elif action == "return":
            prev_order = current_node_order - 1
            if prev_order < 1:
                raise BizOpsError(BizOpsErrorCode.FLOW_STATE_TRANSITION_DENIED, "已在第一节点，无法退回")
            return {"status": "returned", "next_node": prev_order, "is_final": False}

        elif action == "add_sign":
            return {"status": "add_sign", "next_node": current_node_order, "is_final": False}

        elif action == "transfer":
            return {"status": "transfer", "next_node": current_node_order, "is_final": False}

        elif action == "delegate":
            return {"status": "delegate", "next_node": current_node_order, "is_final": False}

        else:
            raise BizOpsError(BizOpsErrorCode.FLOW_STATE_TRANSITION_DENIED, f"未知审批操作: {action}")

    def route_approvers(
        self,
        flow: ApprovalFlowAggregate,
        node_order: int,
        context: dict,
    ) -> list[UUID]:
        """路由当前节点的审批人。"""
        node = flow._find_node(node_order)
        if node is None:
            raise BizOpsError(BizOpsErrorCode.FLOW_NODE_INVALID, f"节点不存在: {node_order}")
        strategy = get_routing_strategy(node.routing_strategy)
        return strategy.route(node.routing_config, context)

    def check_countersign(
        self,
        node_order: int,
        flow: ApprovalFlowAggregate,
        approved_count: int,
        total_count: int,
    ) -> bool:
        """检查会签是否通过。"""
        node = flow._find_node(node_order)
        if node is None or not node.is_countersign:
            return True
        ratio = approved_count / total_count if total_count > 0 else 0
        return ratio >= node.countersign_ratio