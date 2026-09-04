"""ApprovalFlowAggregate - 审批流聚合根，封装多节点审批流定义。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.biz_ops.enums.enums import TimeoutStrategy
from app.domain.biz_ops.value_objects.approval_node import ApprovalNode
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class ApprovalFlowAggregate(AggregateRoot):
    """审批流聚合根 - 多节点审批流定义。

    审批操作语义：同意（推进下一节点）、拒绝（退回起草人）、退回（退回上一节点）、
    加签（增加审批人）、转签（转交他人）、委托（委托代审）
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        flow_key: str,
        flow_name: str,
        entity_type: str,
        nodes: list[ApprovalNode] | None = None,
        is_active: bool = True,
        version: int = 1,
        description: str | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._flow_key = flow_key
        self._flow_name = flow_name
        self._entity_type = entity_type
        self._nodes: list[ApprovalNode] = nodes or []
        self._is_active = is_active
        self._version = version
        self._description = description
        self.validate()

    @property
    def tenant_id(self) -> UUID: return self._tenant_id
    @property
    def flow_key(self) -> str: return self._flow_key
    @property
    def flow_name(self) -> str: return self._flow_name
    @property
    def entity_type(self) -> str: return self._entity_type
    @property
    def nodes(self) -> list[ApprovalNode]: return self._nodes
    @property
    def is_active(self) -> bool: return self._is_active
    @property
    def version(self) -> int: return self._version
    @property
    def description(self) -> str | None: return self._description

    def add_node(self, node: ApprovalNode) -> ApprovalFlowAggregate:
        """添加审批节点 - 返回新实例。"""
        new_nodes = list(self._nodes) + [node]
        return ApprovalFlowAggregate(
            id=self._id, tenant_id=self._tenant_id, flow_key=self._flow_key,
            flow_name=self._flow_name, entity_type=self._entity_type,
            nodes=new_nodes, is_active=self._is_active, version=self._version + 1,
            description=self._description,
        )

    def route_node(self, node_order: int, context: dict) -> dict:
        """路由审批人 - 返回审批人或审批人组。"""
        node = self._find_node(node_order)
        if node is None:
            raise BizOpsError(BizOpsErrorCode.FLOW_NODE_INVALID, f"节点不存在: {node_order}")
        return {
            "node_order": node.node_order,
            "routing_strategy": node.routing_strategy.value,
            "routing_config": node.routing_config,
        }

    def _find_node(self, node_order: int) -> ApprovalNode | None:
        for n in self._nodes:
            if n.node_order == node_order:
                return n
        return None

    def validate(self) -> None:
        if not self._flow_key or len(self._flow_key) > 100:
            raise BizOpsError(BizOpsErrorCode.FLOW_NODE_INVALID, "flow_key 不能为空且不超过 100 字符")
        if self._nodes:
            orders = [n.node_order for n in self._nodes]
            if orders != sorted(orders):
                raise BizOpsError(BizOpsErrorCode.FLOW_NODE_INVALID, "节点顺序必须连续递增")
            if len(orders) != len(set(orders)):
                raise BizOpsError(BizOpsErrorCode.FLOW_NODE_INVALID, "节点顺序不能重复")