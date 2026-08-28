"""T06 租户级业务规则单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.audit.audit_entry import AuditAction, AuditEntry
from app.domain.rules.approval_workflow import (
    ApprovalAction,
    ApprovalThreshold,
    ApprovalWorkflowAggregate,
)
from app.domain.rules.tenant_strategies import (
    InventoryPolicy,
    PricingPolicy,
    TaxPolicy,
)
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import DomainError, ErrorCode


class TestApprovalWorkflow:
    def _make_workflow(self) -> ApprovalWorkflowAggregate:
        wf = ApprovalWorkflowAggregate(EntityId.generate(), uuid4(), "purchase_order")
        wf.add_threshold(ApprovalThreshold(0, 10000, ApprovalAction.AUTO_APPROVE))
        wf.add_threshold(ApprovalThreshold(10000, 50000, ApprovalAction.DEPT_MANAGER))
        wf.add_threshold(ApprovalThreshold(50000, float("inf"), ApprovalAction.GENERAL_MANAGER))
        return wf

    def test_route_auto_approve(self) -> None:
        wf = self._make_workflow()
        assert wf.route(5000) == ApprovalAction.AUTO_APPROVE

    def test_route_dept_manager(self) -> None:
        wf = self._make_workflow()
        assert wf.route(25000) == ApprovalAction.DEPT_MANAGER

    def test_route_general_manager(self) -> None:
        wf = self._make_workflow()
        assert wf.route(100000) == ApprovalAction.GENERAL_MANAGER

    def test_route_incomplete_workflow_raises(self) -> None:
        wf = ApprovalWorkflowAggregate(EntityId.generate(), uuid4(), "po")
        wf.add_threshold(ApprovalThreshold(0, 10000, ApprovalAction.AUTO_APPROVE))
        with pytest.raises(DomainError) as exc:
            wf.route(15000)
        assert exc.value.code == ErrorCode.WORKFLOW_INCOMPLETE

    def test_is_complete_full_coverage(self) -> None:
        wf = self._make_workflow()
        assert wf.is_complete() is True

    def test_is_complete_partial_coverage(self) -> None:
        wf = ApprovalWorkflowAggregate(EntityId.generate(), uuid4(), "po")
        wf.add_threshold(ApprovalThreshold(0, 10000, ApprovalAction.AUTO_APPROVE))
        assert wf.is_complete() is False

    def test_is_complete_empty(self) -> None:
        wf = ApprovalWorkflowAggregate(EntityId.generate(), uuid4(), "po")
        assert wf.is_complete() is False

    def test_thresholds_sorted(self) -> None:
        wf = ApprovalWorkflowAggregate(EntityId.generate(), uuid4(), "po")
        wf.add_threshold(ApprovalThreshold(50000, float("inf"), ApprovalAction.GENERAL_MANAGER))
        wf.add_threshold(ApprovalThreshold(0, 10000, ApprovalAction.AUTO_APPROVE))
        wf.add_threshold(ApprovalThreshold(10000, 50000, ApprovalAction.DEPT_MANAGER))
        assert wf.route(5000) == ApprovalAction.AUTO_APPROVE
        assert wf.route(25000) == ApprovalAction.DEPT_MANAGER


class TestTenantStrategies:
    def test_inventory_policy_defaults(self) -> None:
        policy = InventoryPolicy(tenant_id=uuid4())
        assert policy.allow_negative is False
        assert policy.require_batch is False

    def test_inventory_policy_custom(self) -> None:
        policy = InventoryPolicy(tenant_id=uuid4(), allow_negative=True, require_batch=True)
        assert policy.allow_negative is True
        assert policy.require_batch is True

    def test_tax_policy_defaults(self) -> None:
        policy = TaxPolicy(tenant_id=uuid4())
        assert policy.default_tax_rate == 0.13
        assert policy.tax_inclusive is False

    def test_tax_policy_custom(self) -> None:
        policy = TaxPolicy(tenant_id=uuid4(), default_tax_rate=0.06, tax_inclusive=True)
        assert policy.default_tax_rate == 0.06
        assert policy.tax_inclusive is True

    def test_pricing_policy_defaults(self) -> None:
        policy = PricingPolicy(tenant_id=uuid4())
        assert policy.base_currency == "CNY"
        assert policy.allow_manual_override is True

    def test_pricing_policy_custom(self) -> None:
        policy = PricingPolicy(tenant_id=uuid4(), base_currency="USD", min_profit_margin=0.15)
        assert policy.base_currency == "USD"
        assert policy.min_profit_margin == 0.15

    def test_strategies_tenant_isolated(self) -> None:
        tenant_a = uuid4()
        tenant_b = uuid4()
        policy_a = InventoryPolicy(tenant_id=tenant_a, allow_negative=True)
        policy_b = InventoryPolicy(tenant_id=tenant_b, allow_negative=False)
        assert policy_a.tenant_id != policy_b.tenant_id
        assert policy_a.allow_negative != policy_b.allow_negative


class TestAuditEntry:
    def test_create_audit_entry(self) -> None:
        tenant_id = uuid4()
        entry = AuditEntry.create(
            tenant_id=tenant_id,
            user_id=uuid4(),
            action=AuditAction.CREATE,
            entity_type="purchase_order",
            entity_id="PO-001",
        )
        assert entry.tenant_id == tenant_id
        assert entry.action == AuditAction.CREATE
        assert entry.occurred_at is not None

    def test_audit_entry_immutable(self) -> None:
        entry = AuditEntry.create(
            tenant_id=uuid4(),
            user_id=None,
            action=AuditAction.UPDATE,
            entity_type="config",
            entity_id="tax_rate",
            old_value={"rate": 0.13},
            new_value={"rate": 0.10},
        )
        with pytest.raises(AttributeError):
            entry.action = AuditAction.DELETE  # type: ignore[misc]

    def test_audit_entry_with_ip(self) -> None:
        entry = AuditEntry.create(
            tenant_id=uuid4(),
            user_id=uuid4(),
            action=AuditAction.LOGIN,
            entity_type="session",
            entity_id="sess-001",
            ip_address="192.168.1.100",
        )
        assert entry.ip_address == "192.168.1.100"

    def test_audit_entry_datascope_violation(self) -> None:
        entry = AuditEntry.create(
            tenant_id=uuid4(),
            user_id=uuid4(),
            action=AuditAction.DATASCOPE_VIOLATION,
            entity_type="tenant",
            entity_id=str(uuid4()),
        )
        assert entry.action == AuditAction.DATASCOPE_VIOLATION