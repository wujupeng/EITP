"""BIZ-OPS 端到端测试 - 采购/销售/库存/仓库四大业务操作编排全路径。"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest

from app.domain.biz_ops.aggregates.operation_audit_aggregate import OperationAuditAggregate
from app.domain.biz_ops.enums.enums import OperationType
from app.domain.biz_ops.value_objects.audit_records import CreditCheckResult, PricingApplyRecord
from app.domain.shared.entity import EntityId


TENANT_ID = uuid4()
USER_ID = uuid4()


class TestBizOpsE2E:
    """BIZ-OPS 端到端编排测试。"""

    def test_purchase_operation_audit_chain(self):
        agg = OperationAuditAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, trace_id="trace_001",
            operation_type=OperationType.PURCHASE_ORDER_CREATE, operator_id=USER_ID,
            entity_type="purchase_order", entity_id=uuid4(),
            pricing_records=(PricingApplyRecord(
                strategy_id=uuid4(), strategy_type="supplier_agreement",
                base_price=100.0, final_price=95.0,
            ),),
        )
        d = agg.to_dict()
        assert d["operation_type"] == "purchase_order_create"
        assert len(d["pricing_records"]) == 1
        assert d["pricing_records"][0]["final_price"] == 95.0

    def test_sales_operation_with_credit_check(self):
        credit = CreditCheckResult(
            customer_id=uuid4(), used_amount=8000, credit_limit=10000,
            passed=True, message="信用检查通过",
        )
        agg = OperationAuditAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, trace_id="trace_002",
            operation_type=OperationType.SALES_ORDER_CREATE, operator_id=USER_ID,
            entity_type="sales_order", entity_id=uuid4(),
            credit_check=credit,
        )
        d = agg.to_dict()
        assert d["credit_check"]["passed"] is True
        assert d["credit_check"]["used_amount"] == 8000

    def test_inventory_operation_audit(self):
        agg = OperationAuditAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, trace_id="trace_003",
            operation_type=OperationType.INVENTORY_OUTBOUND, operator_id=USER_ID,
            entity_type="inventory_movement", entity_id=uuid4(),
        )
        d = agg.to_dict()
        assert d["operation_type"] == "inventory_outbound"

    def test_warehouse_operation_with_linkage(self):
        agg = OperationAuditAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, trace_id="trace_004",
            operation_type=OperationType.WAREHOUSE_RECEIVING, operator_id=USER_ID,
            entity_type="warehouse_task", entity_id=uuid4(),
            extra={"linkage_suggestions": ["建议上架", "建议质检"]},
        )
        d = agg.to_dict()
        assert d["extra"]["linkage_suggestions"] == ["建议上架", "建议质检"]

    def test_full_audit_chain_serialization(self):
        agg = OperationAuditAggregate(
            id=EntityId.generate(), tenant_id=TENANT_ID, trace_id="trace_005",
            operation_type=OperationType.PURCHASE_RETURN, operator_id=USER_ID,
            entity_type="purchase_return", entity_id=uuid4(),
            extra={"idempotency_key": "idem_001"},
        )
        d = agg.to_dict()
        assert d["trace_id"] == "trace_005"
        assert d["extra"]["idempotency_key"] == "idem_001"