"""ApprovalFlowAggregate 单元测试 - 多节点、会签、加签转签、条件分支。"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.approval_flow_aggregate import ApprovalFlowAggregate
from app.domain.biz_ops.enums.enums import RoutingStrategyType, TimeoutStrategy
from app.domain.biz_ops.value_objects.approval_node import ApprovalNode
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


TENANT_ID = uuid4()


class TestApprovalFlowAggregate:
    """审批流聚合根测试。"""

    def test_create_empty_flow(self):
        agg = ApprovalFlowAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, flow_key="pur_approval",
            flow_name="采购审批流", entity_type="purchase_order",
        )
        assert agg.flow_key == "pur_approval"
        assert len(agg.nodes) == 0

    def test_add_node(self):
        agg = ApprovalFlowAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, flow_key="pur_approval",
            flow_name="采购审批流", entity_type="purchase_order",
        )
        node = ApprovalNode(node_order=1, node_name="部门审批", routing_strategy=RoutingStrategyType.ROLE)
        updated = agg.add_node(node)
        assert len(updated.nodes) == 1
        assert updated.version == 2

    def test_multi_node_flow(self):
        n1 = ApprovalNode(node_order=1, node_name="部门审批", routing_strategy=RoutingStrategyType.ROLE)
        n2 = ApprovalNode(node_order=2, node_name="财务审批", routing_strategy=RoutingStrategyType.AMOUNT)
        n3 = ApprovalNode(node_order=3, node_name="总经理审批", routing_strategy=RoutingStrategyType.ROLE)
        agg = ApprovalFlowAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, flow_key="pur_approval",
            flow_name="采购审批流", entity_type="purchase_order", nodes=[n1, n2, n3],
        )
        assert len(agg.nodes) == 3

    def test_countersign_node(self):
        node = ApprovalNode(
            node_order=1, node_name="会签节点", routing_strategy=RoutingStrategyType.ROLE,
            is_countersign=True, countersign_ratio=0.6,
        )
        agg = ApprovalFlowAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, flow_key="cs_flow",
            flow_name="会签流", entity_type="document", nodes=[node],
        )
        assert agg.nodes[0].is_countersign is True
        assert agg.nodes[0].countersign_ratio == 0.6

    def test_duplicate_node_order_raises(self):
        n1 = ApprovalNode(node_order=1, node_name="节点1", routing_strategy=RoutingStrategyType.ROLE)
        n2 = ApprovalNode(node_order=1, node_name="节点2", routing_strategy=RoutingStrategyType.ROLE)
        with pytest.raises(BizOpsError):
            ApprovalFlowAggregate(
                id=EntityId.generate(), tenant_id=TENANT_ID, flow_key="dup_flow",
                flow_name="重复节点流", entity_type="doc", nodes=[n1, n2],
            )

    def test_route_node(self):
        node = ApprovalNode(
            node_order=1, node_name="金额审批", routing_strategy=RoutingStrategyType.AMOUNT,
            routing_config={"threshold": 10000, "normal_users": ["uuid1"], "escalate_users": ["uuid2"]},
        )
        agg = ApprovalFlowAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, flow_key="amt_flow",
            flow_name="金额审批流", entity_type="invoice", nodes=[node],
        )
        result = agg.route_node(1, {"amount": 5000})
        assert result["node_order"] == 1
        assert result["routing_strategy"] == "amount"