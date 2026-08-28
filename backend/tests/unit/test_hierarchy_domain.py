"""T02 领域层单元测试 - 聚合根行为、校验服务、异常拒绝。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.hierarchy.hierarchy_aggregate import HierarchyAggregate
from app.domain.hierarchy.hierarchy_node import HierarchyLevel, HierarchyNode
from app.domain.hierarchy.hierarchy_validator import HierarchyValidator
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import ErrorCode, HierarchyError


def _make_node(
    level: HierarchyLevel,
    tenant_id=None,
    parent_id=None,
    is_active=True,
) -> HierarchyNode:
    return HierarchyNode(
        id=EntityId.generate(),
        tenant_id=tenant_id or uuid4(),
        level=level,
        name=f"Test-{level.name}",
        parent_id=parent_id,
        is_active=is_active,
    )


class TestHierarchyNode:
    def test_disable_sets_inactive(self) -> None:
        node = _make_node(HierarchyLevel.ENTERPRISE)
        assert node.is_active is True
        node.disable()
        assert node.is_active is False

    def test_enable_sets_active(self) -> None:
        node = _make_node(HierarchyLevel.ENTERPRISE, is_active=False)
        assert node.is_active is False
        node.enable()
        assert node.is_active is True

    def test_rename_updates_name(self) -> None:
        node = _make_node(HierarchyLevel.ENTERPRISE)
        node.rename("New Name")
        assert node.name == "New Name"

    def test_rename_empty_raises(self) -> None:
        node = _make_node(HierarchyLevel.ENTERPRISE)
        with pytest.raises(ValueError):
            node.rename("")


class TestHierarchyAggregate:
    def test_add_node_success(self) -> None:
        tenant_id = uuid4()
        agg = HierarchyAggregate(EntityId.generate(), tenant_id)
        node = _make_node(HierarchyLevel.ENTERPRISE, tenant_id=tenant_id)
        agg.add_node(node, parent_depth=2)
        assert len(agg.nodes) == 1

    def test_add_node_depth_exceeded(self) -> None:
        tenant_id = uuid4()
        agg = HierarchyAggregate(EntityId.generate(), tenant_id)
        node = _make_node(HierarchyLevel.LOCATION, tenant_id=tenant_id)
        with pytest.raises(HierarchyError) as exc:
            agg.add_node(node, parent_depth=7)
        assert exc.value.code == ErrorCode.HIERARCHY_DEPTH_EXCEEDED

    def test_add_node_cross_tenant(self) -> None:
        tenant_a = uuid4()
        tenant_b = uuid4()
        agg = HierarchyAggregate(EntityId.generate(), tenant_a)
        node = _make_node(HierarchyLevel.ENTERPRISE, tenant_id=tenant_b)
        with pytest.raises(HierarchyError) as exc:
            agg.add_node(node, parent_depth=2)
        assert exc.value.code == ErrorCode.HIERARCHY_CROSS_TENANT

    def test_disable_node_records_event(self) -> None:
        tenant_id = uuid4()
        agg = HierarchyAggregate(EntityId.generate(), tenant_id)
        node = _make_node(HierarchyLevel.ENTERPRISE, tenant_id=tenant_id)
        agg.add_node(node, parent_depth=2)
        agg.disable_node(node.id.value)
        events = list(agg.pull_events())
        assert len(events) == 2
        assert events[1].event_type == "HierarchyNodeDisabledEvent"

    def test_get_children(self) -> None:
        tenant_id = uuid4()
        agg = HierarchyAggregate(EntityId.generate(), tenant_id)
        parent = _make_node(HierarchyLevel.ENTERPRISE, tenant_id=tenant_id)
        child = HierarchyNode(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            level=HierarchyLevel.ORGANIZATION,
            name="Child",
            parent_id=parent.id,
        )
        agg.add_node(parent, parent_depth=2)
        agg.add_node(child, parent_depth=3)
        children = agg.get_children(parent.id.value)
        assert len(children) == 1
        assert children[0].name == "Child"


class TestHierarchyValidator:
    def test_validate_parent_platform_no_parent(self) -> None:
        HierarchyValidator.validate_parent(HierarchyLevel.PLATFORM, None, uuid4())

    def test_validate_parent_platform_with_parent_raises(self) -> None:
        parent = _make_node(HierarchyLevel.PLATFORM)
        with pytest.raises(HierarchyError):
            HierarchyValidator.validate_parent(HierarchyLevel.PLATFORM, parent, parent.tenant_id)

    def test_validate_parent_cross_tenant_raises(self) -> None:
        tenant_a = uuid4()
        tenant_b = uuid4()
        parent = _make_node(HierarchyLevel.TENANT, tenant_id=tenant_a)
        with pytest.raises(HierarchyError) as exc:
            HierarchyValidator.validate_parent(HierarchyLevel.ENTERPRISE, parent, tenant_b)
        assert exc.value.code == ErrorCode.HIERARCHY_CROSS_TENANT

    def test_validate_parent_wrong_level_raises(self) -> None:
        tenant_id = uuid4()
        parent = _make_node(HierarchyLevel.ENTERPRISE, tenant_id=tenant_id)
        with pytest.raises(HierarchyError):
            HierarchyValidator.validate_parent(HierarchyLevel.SITE, parent, tenant_id)

    def test_validate_no_circular_ref_detects_cycle(self) -> None:
        node_a = uuid4()
        node_b = uuid4()
        ancestor_chain = {node_a: node_b, node_b: node_a}
        with pytest.raises(HierarchyError) as exc:
            HierarchyValidator.validate_no_circular_ref(node_a, node_b, ancestor_chain)
        assert exc.value.code == ErrorCode.HIERARCHY_CIRCULAR_REF

    def test_validate_no_circular_ref_no_cycle(self) -> None:
        node_a = uuid4()
        node_b = uuid4()
        node_c = uuid4()
        ancestor_chain = {node_b: node_c, node_c: None}
        HierarchyValidator.validate_no_circular_ref(node_a, node_b, ancestor_chain)

    def test_validate_depth_ok(self) -> None:
        HierarchyValidator.validate_depth(7)

    def test_validate_depth_exceeded(self) -> None:
        with pytest.raises(HierarchyError) as exc:
            HierarchyValidator.validate_depth(8)
        assert exc.value.code == ErrorCode.HIERARCHY_DEPTH_EXCEEDED