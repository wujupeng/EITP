"""T07 集团模式与跨公司报表单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.audit.audit_entry import AuditAction
from app.domain.group.group_aggregate import GroupAggregate, PropagateResult
from app.domain.group.group_events import (
    BusinessChangedEvent,
    GroupReportQueriedEvent,
    MasterDataPropagatedEvent,
    ReadonlyViolationEvent,
)
from app.domain.group.readonly_boundary import (
    GroupActor,
    OperationType,
    ReadonlyBoundary,
    SubsidiaryIsolationGuard,
)
from app.domain.group.summary_snapshot import ReportDimension, SummarySnapshot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import DomainError, ErrorCode


class TestReadonlyBoundary:
    """T07-01: 集团管理员只读边界。"""

    def _make_group_admin(self) -> GroupActor:
        return GroupActor(
            actor_id=uuid4(),
            enterprise_id=uuid4(),
            is_group_admin=True,
        )

    def test_group_admin_read_allowed(self) -> None:
        actor = self._make_group_admin()
        ReadonlyBoundary.enforce(actor, OperationType.READ, uuid4())

    def test_group_admin_create_rejected(self) -> None:
        actor = self._make_group_admin()
        with pytest.raises(DomainError) as exc:
            ReadonlyBoundary.enforce(actor, OperationType.CREATE, uuid4())
        assert exc.value.code == ErrorCode.GROUP_READONLY_VIOLATION

    def test_group_admin_update_rejected(self) -> None:
        actor = self._make_group_admin()
        with pytest.raises(DomainError) as exc:
            ReadonlyBoundary.enforce(actor, OperationType.UPDATE, uuid4())
        assert exc.value.code == ErrorCode.GROUP_READONLY_VIOLATION

    def test_group_admin_delete_rejected(self) -> None:
        actor = self._make_group_admin()
        with pytest.raises(DomainError) as exc:
            ReadonlyBoundary.enforce(actor, OperationType.DELETE, uuid4())
        assert exc.value.code == ErrorCode.GROUP_READONLY_VIOLATION

    def test_group_admin_approve_rejected(self) -> None:
        actor = self._make_group_admin()
        with pytest.raises(DomainError) as exc:
            ReadonlyBoundary.enforce(actor, OperationType.APPROVE, uuid4())
        assert exc.value.code == ErrorCode.GROUP_READONLY_VIOLATION

    def test_non_group_admin_write_allowed(self) -> None:
        actor = GroupActor(
            actor_id=uuid4(),
            enterprise_id=uuid4(),
            is_group_admin=False,
        )
        ReadonlyBoundary.enforce(actor, OperationType.CREATE, uuid4())
        ReadonlyBoundary.enforce(actor, OperationType.UPDATE, uuid4())

    def test_audit_violation_records_entry(self) -> None:
        actor = self._make_group_admin()
        entry = ReadonlyBoundary.audit_violation(
            actor, OperationType.UPDATE, uuid4()
        )
        assert entry.action == AuditAction.GROUP_READONLY_VIOLATION

    def test_build_violation_event(self) -> None:
        actor = self._make_group_admin()
        target_org = uuid4()
        event = ReadonlyBoundary.build_violation_event(
            actor, OperationType.DELETE, target_org
        )
        assert isinstance(event, ReadonlyViolationEvent)
        assert event.operation == "delete"
        assert event.target_organization_id == target_org

    def test_operation_type_is_write(self) -> None:
        assert OperationType.READ.is_write is False
        assert OperationType.CREATE.is_write is True
        assert OperationType.UPDATE.is_write is True
        assert OperationType.DELETE.is_write is True
        assert OperationType.APPROVE.is_write is True
        assert OperationType.REJECT.is_write is True


class TestSubsidiaryIsolation:
    """T07-02: 子公司管理员隔离。"""

    def test_same_organization_allowed(self) -> None:
        org_id = uuid4()
        SubsidiaryIsolationGuard.enforce(org_id, org_id, uuid4())

    def test_different_organization_denied(self) -> None:
        with pytest.raises(DomainError) as exc:
            SubsidiaryIsolationGuard.enforce(uuid4(), uuid4(), uuid4())
        assert exc.value.code == ErrorCode.SUBSIDIARY_ISOLATION_VIOLATION

    def test_filter_visible_returns_only_own(self) -> None:
        own = uuid4()
        others = (uuid4(), uuid4())
        visible = SubsidiaryIsolationGuard.filter_visible(own, (own, *others))
        assert visible == (own,)

    def test_filter_visible_empty_when_not_in_list(self) -> None:
        own = uuid4()
        visible = SubsidiaryIsolationGuard.filter_visible(own, (uuid4(), uuid4()))
        assert visible == ()


class TestSummarySnapshot:
    """T07-03: 汇总快照与延迟标记。"""

    def test_create_snapshot(self) -> None:
        enterprise = uuid4()
        org = uuid4()
        snapshot = SummarySnapshot.create(
            enterprise_id=enterprise,
            organization_id=org,
            dimension=ReportDimension.SALES,
            snapshot_value={"total": 10000.0, "count": 5},
        )
        assert snapshot.enterprise_id == enterprise
        assert snapshot.organization_id == org
        assert snapshot.dimension == ReportDimension.SALES
        assert snapshot.snapshot_value["total"] == 10000.0

    def test_is_delayed_within_threshold(self) -> None:
        now = datetime.now(timezone.utc)
        snapshot = SummarySnapshot.create(
            enterprise_id=uuid4(),
            organization_id=uuid4(),
            dimension=ReportDimension.SALES,
            snapshot_value={},
            snapshot_at=now - timedelta(seconds=60),
        )
        assert snapshot.is_delayed(now) is False

    def test_is_delayed_exceeds_threshold(self) -> None:
        now = datetime.now(timezone.utc)
        snapshot = SummarySnapshot.create(
            enterprise_id=uuid4(),
            organization_id=uuid4(),
            dimension=ReportDimension.SALES,
            snapshot_value={},
            snapshot_at=now - timedelta(seconds=301),
        )
        assert snapshot.is_delayed(now) is True

    def test_is_delayed_default_now(self) -> None:
        snapshot = SummarySnapshot.create(
            enterprise_id=uuid4(),
            organization_id=uuid4(),
            dimension=ReportDimension.SALES,
            snapshot_value={},
        )
        assert snapshot.is_delayed() is False

    def test_merge_numeric_values(self) -> None:
        s1 = SummarySnapshot.create(
            enterprise_id=uuid4(),
            organization_id=uuid4(),
            dimension=ReportDimension.SALES,
            snapshot_value={"total": 100.0, "count": 3},
        )
        s2 = SummarySnapshot.create(
            enterprise_id=uuid4(),
            organization_id=uuid4(),
            dimension=ReportDimension.SALES,
            snapshot_value={"total": 200.0, "count": 5},
        )
        merged = s1.merge(s2)
        assert merged["total"] == 300.0
        assert merged["count"] == 8

    def test_merge_non_numeric_overwrites(self) -> None:
        s1 = SummarySnapshot.create(
            enterprise_id=uuid4(),
            organization_id=uuid4(),
            dimension=ReportDimension.SALES,
            snapshot_value={"label": "A", "total": 100.0},
        )
        s2 = SummarySnapshot.create(
            enterprise_id=uuid4(),
            organization_id=uuid4(),
            dimension=ReportDimension.SALES,
            snapshot_value={"label": "B", "total": 200.0},
        )
        merged = s1.merge(s2)
        assert merged["label"] == "B"
        assert merged["total"] == 300.0


class TestGroupAggregate:
    """T07-01/03/05: 集团聚合根 - 汇总、只读边界、主数据下发。"""

    def _make_aggregate(self, org_count: int = 3) -> tuple[GroupAggregate, list[UUID]]:
        enterprise = uuid4()
        agg = GroupAggregate(EntityId.generate(), enterprise)
        orgs = [uuid4() for _ in range(org_count)]
        for org in orgs:
            agg.add_organization(org)
        return agg, orgs

    def test_add_remove_organization(self) -> None:
        agg, orgs = self._make_aggregate(2)
        assert len(agg.organizations) == 2
        agg.remove_organization(orgs[0])
        assert orgs[0] not in agg.organizations
        assert len(agg.organizations) == 1

    def test_aggregate_report_no_snapshots(self) -> None:
        agg, _ = self._make_aggregate(3)
        summary, is_delayed, count = agg.aggregate_report(ReportDimension.SALES)
        assert summary == {}
        assert is_delayed is False
        assert count == 0

    def test_aggregate_report_with_snapshots(self) -> None:
        agg, orgs = self._make_aggregate(3)
        now = datetime.now(timezone.utc)
        for org in orgs:
            snapshot = SummarySnapshot.create(
                enterprise_id=agg.enterprise_id,
                organization_id=org,
                dimension=ReportDimension.SALES,
                snapshot_value={"total": 1000.0, "count": 10},
                snapshot_at=now,
            )
            agg.update_snapshot(snapshot)

        summary, is_delayed, count = agg.aggregate_report(
            ReportDimension.SALES, now=now
        )
        assert summary["total"] == 3000.0
        assert summary["count"] == 30
        assert is_delayed is False
        assert count == 3

    def test_aggregate_report_delayed_snapshot(self) -> None:
        agg, orgs = self._make_aggregate(2)
        now = datetime.now(timezone.utc)
        for org in orgs:
            snapshot = SummarySnapshot.create(
                enterprise_id=agg.enterprise_id,
                organization_id=org,
                dimension=ReportDimension.SALES,
                snapshot_value={"total": 500.0},
                snapshot_at=now - timedelta(seconds=400),
            )
            agg.update_snapshot(snapshot)

        summary, is_delayed, count = agg.aggregate_report(
            ReportDimension.SALES, now=now
        )
        assert is_delayed is True
        assert count == 2

    def test_aggregate_report_partial_delay(self) -> None:
        agg, orgs = self._make_aggregate(2)
        now = datetime.now(timezone.utc)
        fresh = SummarySnapshot.create(
            enterprise_id=agg.enterprise_id,
            organization_id=orgs[0],
            dimension=ReportDimension.SALES,
            snapshot_value={"total": 100.0},
            snapshot_at=now,
        )
        stale = SummarySnapshot.create(
            enterprise_id=agg.enterprise_id,
            organization_id=orgs[1],
            dimension=ReportDimension.SALES,
            snapshot_value={"total": 200.0},
            snapshot_at=now - timedelta(seconds=400),
        )
        agg.update_snapshot(fresh)
        agg.update_snapshot(stale)

        _, is_delayed, count = agg.aggregate_report(
            ReportDimension.SALES, now=now
        )
        assert is_delayed is True
        assert count == 2

    def test_aggregate_report_specific_orgs(self) -> None:
        agg, orgs = self._make_aggregate(3)
        now = datetime.now(timezone.utc)
        for org in orgs:
            snapshot = SummarySnapshot.create(
                enterprise_id=agg.enterprise_id,
                organization_id=org,
                dimension=ReportDimension.PURCHASE,
                snapshot_value={"total": 500.0},
                snapshot_at=now,
            )
            agg.update_snapshot(snapshot)

        summary, _, count = agg.aggregate_report(
            ReportDimension.PURCHASE,
            organization_ids=(orgs[0], orgs[1]),
            now=now,
        )
        assert summary["total"] == 1000.0
        assert count == 2

    def test_aggregate_report_emits_event(self) -> None:
        agg, _ = self._make_aggregate(1)
        agg.aggregate_report(ReportDimension.SALES)
        events = list(agg.pull_events())
        assert any(isinstance(e, GroupReportQueriedEvent) for e in events)

    def test_update_snapshot_cross_enterprise_rejected(self) -> None:
        agg, _ = self._make_aggregate(1)
        snapshot = SummarySnapshot.create(
            enterprise_id=uuid4(),
            organization_id=uuid4(),
            dimension=ReportDimension.SALES,
            snapshot_value={},
        )
        with pytest.raises(DomainError) as exc:
            agg.update_snapshot(snapshot)
        assert exc.value.code == ErrorCode.GROUP_READONLY_VIOLATION

    def test_enforce_readonly_delegates_to_boundary(self) -> None:
        agg, orgs = self._make_aggregate(1)
        actor = GroupActor(
            actor_id=uuid4(),
            enterprise_id=agg.enterprise_id,
            is_group_admin=True,
        )
        with pytest.raises(DomainError) as exc:
            agg.enforce_readonly(actor, OperationType.UPDATE, orgs[0])
        assert exc.value.code == ErrorCode.GROUP_READONLY_VIOLATION

    def test_snapshot_delay_threshold(self) -> None:
        assert GroupAggregate.snapshot_delay_threshold() == 300

    def test_aggregation_timeout(self) -> None:
        assert GroupAggregate.aggregation_timeout() == 3.0


class TestPropagateMasterData:
    """T07-05: 集团主数据下发。"""

    def _make_aggregate(self, org_count: int = 3) -> tuple[GroupAggregate, list[UUID]]:
        enterprise = uuid4()
        agg = GroupAggregate(EntityId.generate(), enterprise)
        orgs = [uuid4() for _ in range(org_count)]
        for org in orgs:
            agg.add_organization(org)
        return agg, orgs

    def test_propagate_all_succeed(self) -> None:
        agg, orgs = self._make_aggregate(3)
        result = agg.propagate_master_data(
            master_data_type="sku",
            master_data_id="SKU-001",
            target_org_ids=tuple(orgs),
        )
        assert len(result.succeeded) == 3
        assert len(result.failed) == 0
        assert len(result.conflicts) == 0
        assert result.has_conflict is False

    def test_propagate_with_conflict(self) -> None:
        agg, orgs = self._make_aggregate(3)
        existing = {orgs[1]: {"SKU-001"}}
        result = agg.propagate_master_data(
            master_data_type="sku",
            master_data_id="SKU-001",
            target_org_ids=tuple(orgs),
            existing_codes=existing,
        )
        assert len(result.succeeded) == 2
        assert len(result.conflicts) == 1
        assert result.conflicts[0].organization_id == orgs[1]
        assert result.has_conflict is True

    def test_propagate_unknown_org_fails(self) -> None:
        agg, orgs = self._make_aggregate(2)
        unknown_org = uuid4()
        result = agg.propagate_master_data(
            master_data_type="sku",
            master_data_id="SKU-002",
            target_org_ids=(orgs[0], unknown_org),
        )
        assert orgs[0] in result.succeeded
        assert unknown_org in result.failed
        assert result.has_failure is True

    def test_propagate_emits_event(self) -> None:
        agg, orgs = self._make_aggregate(2)
        agg.propagate_master_data(
            master_data_type="sku",
            master_data_id="SKU-001",
            target_org_ids=tuple(orgs),
        )
        events = list(agg.pull_events())
        assert any(isinstance(e, MasterDataPropagatedEvent) for e in events)

    def test_propagate_all_conflict(self) -> None:
        agg, orgs = self._make_aggregate(2)
        existing = {org: {"SKU-001"} for org in orgs}
        result = agg.propagate_master_data(
            master_data_type="sku",
            master_data_id="SKU-001",
            target_org_ids=tuple(orgs),
            existing_codes=existing,
        )
        assert len(result.succeeded) == 0
        assert len(result.conflicts) == 2


class TestBusinessChangedEvent:
    """T07-03: 业务变更事件驱动异步聚合。"""

    def test_publish_business_changed(self) -> None:
        enterprise = uuid4()
        agg = GroupAggregate(EntityId.generate(), enterprise)
        org = uuid4()
        agg.add_organization(org)

        event = agg.publish_business_changed(
            organization_id=org,
            dimension=ReportDimension.SALES,
            delta=500.0,
            source_version=1,
            tenant_id=uuid4(),
        )
        assert isinstance(event, BusinessChangedEvent)
        assert event.delta == 500.0
        assert event.dimension == "sales"

        events = list(agg.pull_events())
        assert any(isinstance(e, BusinessChangedEvent) for e in events)


class TestReportDimension:
    def test_all_dimensions(self) -> None:
        dims = [d.value for d in ReportDimension]
        assert "sales" in dims
        assert "purchase" in dims
        assert "inventory" in dims
        assert "funds" in dims
        assert "customer" in dims
        assert "supplier" in dims

    def test_dimension_from_string(self) -> None:
        assert ReportDimension("sales") == ReportDimension.SALES
        assert ReportDimension("inventory") == ReportDimension.INVENTORY