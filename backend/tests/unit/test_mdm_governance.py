"""EITP-MDM-001-T16-03 治理工作流与版本管理聚合根单元测试。

覆盖：
- GovernanceWorkflowAggregate 状态机 DRAFT→SUBMITTED→APPROVED→PUBLISHED/REJECTED/ROLLED_BACK
- 非法状态跳转被拒绝、已提交不可修改
- MasterDataVersionAggregate 不可变、版本对比字段级差异、版本回滚恢复前一版本

对应 spec 5.6.1.3 / 5.6.1.11 / 4.2.1，design 2.6。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.governance.aggregates.governance_workflow_aggregate import (
    GovernanceLevel,
    GovernanceWorkflowAggregate,
)
from app.domain.governance.aggregates.master_data_version_aggregate import (
    ChangeType,
    MasterDataVersionAggregate,
)
from app.domain.governance.events.governance_events import (
    GovernanceRequestApprovedEvent,
    GovernanceRequestPublishedEvent,
    GovernanceRequestRejectedEvent,
    GovernanceRequestRollbackEvent,
    GovernanceRequestSubmittedEvent,
)
from app.domain.governance.value_objects.governance_state import (
    GovernanceState,
    is_editable,
    validate_state_transition,
)
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


@pytest.fixture
def target_version_id() -> uuid4:
    return uuid4()


@pytest.fixture
def workflow(target_version_id: uuid4) -> GovernanceWorkflowAggregate:
    return GovernanceWorkflowAggregate(
        id=EntityId.generate(),
        governance_level=GovernanceLevel.GROUP,
        entity_type="group_product",
        target_version_id=target_version_id,
    )


def _diff_versions(
    before: dict,
    after: dict,
) -> list[dict]:
    """字段级差异对比（design 2.6 MasterDataVersionComparator 字段级 diff）。

    返回字段差异列表：[{field, old_value, new_value}]，仅含发生变化的字段。
    """
    diffs: list[dict] = []
    all_keys = set(before.keys()) | set(after.keys())
    for key in all_keys:
        old_value = before.get(key)
        new_value = after.get(key)
        if old_value != new_value:
            diffs.append({"field": key, "old_value": old_value, "new_value": new_value})
    return diffs


class GovernanceStateTest:
    """治理状态流转校验 - 非法跳转被拒绝。"""

    def test_valid_transitions_allowed(self) -> None:
        validate_state_transition(GovernanceState.DRAFT, GovernanceState.SUBMITTED)
        validate_state_transition(GovernanceState.SUBMITTED, GovernanceState.APPROVED)
        validate_state_transition(GovernanceState.SUBMITTED, GovernanceState.REJECTED)
        validate_state_transition(GovernanceState.APPROVED, GovernanceState.PUBLISHED)
        validate_state_transition(GovernanceState.PUBLISHED, GovernanceState.ROLLED_BACK)

    @pytest.mark.parametrize(
        "from_state, to_state",
        [
            (GovernanceState.DRAFT, GovernanceState.APPROVED),
            (GovernanceState.DRAFT, GovernanceState.PUBLISHED),
            (GovernanceState.DRAFT, GovernanceState.REJECTED),
            (GovernanceState.DRAFT, GovernanceState.ROLLED_BACK),
            (GovernanceState.SUBMITTED, GovernanceState.PUBLISHED),
            (GovernanceState.SUBMITTED, GovernanceState.ROLLED_BACK),
            (GovernanceState.APPROVED, GovernanceState.REJECTED),
            (GovernanceState.APPROVED, GovernanceState.ROLLED_BACK),
            (GovernanceState.REJECTED, GovernanceState.SUBMITTED),
            (GovernanceState.REJECTED, GovernanceState.APPROVED),
            (GovernanceState.PUBLISHED, GovernanceState.SUBMITTED),
            (GovernanceState.ROLLED_BACK, GovernanceState.PUBLISHED),
        ],
    )
    def test_invalid_transitions_rejected(
        self, from_state: GovernanceState, to_state: GovernanceState
    ) -> None:
        with pytest.raises(MDMError) as exc:
            validate_state_transition(from_state, to_state)
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    def test_is_editable_only_in_draft(self) -> None:
        assert is_editable(GovernanceState.DRAFT) is True
        assert is_editable(GovernanceState.SUBMITTED) is False
        assert is_editable(GovernanceState.APPROVED) is False
        assert is_editable(GovernanceState.PUBLISHED) is False
        assert is_editable(GovernanceState.REJECTED) is False
        assert is_editable(GovernanceState.ROLLED_BACK) is False


class GovernanceWorkflowAggregateTest:
    """治理工作流聚合根 - 五步状态机。"""

    def test_create_group_level_without_tenant_id(self, target_version_id: uuid4) -> None:
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.GROUP,
            entity_type="group_product",
            target_version_id=target_version_id,
        )
        assert wf.governance_level == GovernanceLevel.GROUP
        assert wf.tenant_id is None
        assert wf.is_group_level() is True
        assert wf.status == GovernanceState.DRAFT
        assert wf.is_editable() is True

    def test_create_group_level_with_tenant_id_rejected(self, target_version_id: uuid4) -> None:
        with pytest.raises(MDMError) as exc:
            GovernanceWorkflowAggregate(
                id=EntityId.generate(),
                governance_level=GovernanceLevel.GROUP,
                entity_type="group_product",
                target_version_id=target_version_id,
                tenant_id=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    def test_create_enterprise_level_requires_tenant_id(self, target_version_id: uuid4) -> None:
        with pytest.raises(MDMError) as exc:
            GovernanceWorkflowAggregate(
                id=EntityId.generate(),
                governance_level=GovernanceLevel.ENTERPRISE,
                entity_type="enterprise_product",
                target_version_id=target_version_id,
            )
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    def test_create_enterprise_level_with_tenant_id(self, target_version_id: uuid4) -> None:
        tenant_id = uuid4()
        wf = GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=GovernanceLevel.ENTERPRISE,
            entity_type="enterprise_product",
            target_version_id=target_version_id,
            tenant_id=tenant_id,
        )
        assert wf.tenant_id == tenant_id
        assert wf.is_group_level() is False

    def test_full_happy_path_draft_to_published(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        submitter = uuid4()
        approver = uuid4()
        publisher = uuid4()

        workflow.submit(submitted_by=submitter)
        assert workflow.status == GovernanceState.SUBMITTED
        assert workflow.is_editable() is False
        assert workflow.submitted_by == submitter
        assert workflow.submitted_at is not None

        workflow.approve(approver=approver, opinion="同意")
        assert workflow.status == GovernanceState.APPROVED
        assert workflow.approved_by == approver
        assert workflow.approval_opinion == "同意"

        workflow.publish(published_by=publisher)
        assert workflow.status == GovernanceState.PUBLISHED
        assert workflow.published_by == publisher
        assert workflow.published_at is not None

        events = list(workflow.pull_events())
        assert len(events) == 3
        assert isinstance(events[0], GovernanceRequestSubmittedEvent)
        assert isinstance(events[1], GovernanceRequestApprovedEvent)
        assert isinstance(events[2], GovernanceRequestPublishedEvent)
        assert events[2].target_version_id == workflow.target_version_id

    def test_reject_path_draft_to_rejected(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        workflow.submit(submitted_by=uuid4())
        rejecter = uuid4()
        workflow.reject(rejecter=rejecter, opinion="不同意")
        assert workflow.status == GovernanceState.REJECTED
        assert workflow.approved_by == rejecter
        assert workflow.approval_opinion == "不同意"
        events = list(workflow.pull_events())
        assert len(events) == 2
        assert isinstance(events[1], GovernanceRequestRejectedEvent)
        assert events[1].rejection_opinion == "不同意"

    def test_rollback_path_published_to_rolled_back(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        workflow.submit(submitted_by=uuid4())
        workflow.approve(approver=uuid4(), opinion="同意")
        workflow.publish(published_by=uuid4())
        rollback_by = uuid4()
        workflow.rollback(rollback_by=rollback_by, reason="发布后发现数据错误")
        assert workflow.status == GovernanceState.ROLLED_BACK
        assert workflow.rollback_by == rollback_by
        assert workflow.rollback_reason == "发布后发现数据错误"
        assert workflow.rollback_at is not None
        events = list(workflow.pull_events())
        assert isinstance(events[-1], GovernanceRequestRollbackEvent)
        assert events[-1].rollback_reason == "发布后发现数据错误"

    def test_submit_from_non_draft_rejected(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        workflow.submit(submitted_by=uuid4())
        with pytest.raises(MDMError) as exc:
            workflow.submit(submitted_by=uuid4())
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION
        assert workflow.status == GovernanceState.SUBMITTED

    def test_approve_from_draft_rejected(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        with pytest.raises(MDMError) as exc:
            workflow.approve(approver=uuid4(), opinion="同意")
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION
        assert workflow.status == GovernanceState.DRAFT

    def test_publish_from_submitted_rejected(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        workflow.submit(submitted_by=uuid4())
        with pytest.raises(MDMError) as exc:
            workflow.publish(published_by=uuid4())
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION
        assert workflow.status == GovernanceState.SUBMITTED

    def test_rollback_from_approved_rejected(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        workflow.submit(submitted_by=uuid4())
        workflow.approve(approver=uuid4(), opinion="同意")
        with pytest.raises(MDMError) as exc:
            workflow.rollback(rollback_by=uuid4(), reason="回滚")
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION
        assert workflow.status == GovernanceState.APPROVED

    def test_rollback_from_draft_rejected(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        with pytest.raises(MDMError) as exc:
            workflow.rollback(rollback_by=uuid4(), reason="回滚")
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    def test_reject_from_approved_rejected(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        workflow.submit(submitted_by=uuid4())
        workflow.approve(approver=uuid4(), opinion="同意")
        with pytest.raises(MDMError) as exc:
            workflow.reject(rejecter=uuid4(), opinion="拒绝")
        assert exc.value.code == MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION

    def test_submit_records_submitted_event(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        submitter = uuid4()
        workflow.submit(submitted_by=submitter)
        events = list(workflow.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, GovernanceRequestSubmittedEvent)
        assert event.submitted_by == submitter
        assert event.governance_level == GovernanceLevel.GROUP.value
        assert event.entity_type == "group_product"

    def test_is_editable_false_after_submit(
        self, workflow: GovernanceWorkflowAggregate
    ) -> None:
        assert workflow.is_editable() is True
        workflow.submit(submitted_by=uuid4())
        assert workflow.is_editable() is False


class MasterDataVersionAggregateTest:
    """主数据版本聚合根 - 不可变 append-only、版本对比、版本回滚。"""

    def _make_snapshot(self, name: str = "商品A", category: str = "食品", price: int = 100) -> dict:
        return {"name": name, "category": category, "price": price}

    def test_create_initial_version(self) -> None:
        entity_id = uuid4()
        operated_by = uuid4()
        version = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=entity_id,
            snapshot_after=self._make_snapshot(),
            operated_by=operated_by,
        )
        assert version.version_number == 1
        assert version.change_type == ChangeType.CREATE
        assert version.snapshot_before is None
        assert version.snapshot_after == self._make_snapshot()
        assert version.entity_id == entity_id
        assert version.operated_by == operated_by
        assert version.operated_at is not None

    def test_create_update_version(self) -> None:
        before = self._make_snapshot(name="旧名")
        after = self._make_snapshot(name="新名")
        version = MasterDataVersionAggregate.create_update(
            entity_type="group_product",
            entity_id=uuid4(),
            version_number=2,
            snapshot_before=before,
            snapshot_after=after,
            operated_by=uuid4(),
        )
        assert version.version_number == 2
        assert version.change_type == ChangeType.UPDATE
        assert version.snapshot_before == before
        assert version.snapshot_after == after

    def test_version_number_must_start_from_one(self) -> None:
        with pytest.raises(MDMError) as exc:
            MasterDataVersionAggregate(
                id=EntityId.generate(),
                entity_type="group_product",
                entity_id=uuid4(),
                version_number=0,
                snapshot_after={},
                change_type=ChangeType.CREATE,
                operated_by=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_version_number_negative_rejected(self) -> None:
        with pytest.raises(MDMError) as exc:
            MasterDataVersionAggregate(
                id=EntityId.generate(),
                entity_type="group_product",
                entity_id=uuid4(),
                version_number=-1,
                snapshot_after={},
                change_type=ChangeType.CREATE,
                operated_by=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_is_group_level_when_tenant_id_none(self) -> None:
        version = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=uuid4(),
            snapshot_after={},
            operated_by=uuid4(),
        )
        assert version.is_group_level() is True
        assert version.tenant_id is None

    def test_is_not_group_level_when_tenant_id_present(self) -> None:
        tenant_id = uuid4()
        version = MasterDataVersionAggregate.create_initial(
            entity_type="enterprise_product",
            entity_id=uuid4(),
            snapshot_after={},
            operated_by=uuid4(),
            tenant_id=tenant_id,
        )
        assert version.is_group_level() is False
        assert version.tenant_id == tenant_id

    def test_version_field_level_diff_detects_changes(self) -> None:
        before = self._make_snapshot(name="旧名", category="食品", price=100)
        after = self._make_snapshot(name="新名", category="食品", price=120)
        diffs = _diff_versions(before, after)
        diff_fields = {d["field"] for d in diffs}
        assert diff_fields == {"name", "price"}
        name_diff = next(d for d in diffs if d["field"] == "name")
        assert name_diff["old_value"] == "旧名"
        assert name_diff["new_value"] == "新名"
        price_diff = next(d for d in diffs if d["field"] == "price")
        assert price_diff["old_value"] == 100
        assert price_diff["new_value"] == 120

    def test_version_field_level_diff_no_changes_returns_empty(self) -> None:
        snapshot = self._make_snapshot()
        assert _diff_versions(snapshot, snapshot) == []

    def test_version_field_level_diff_detects_added_field(self) -> None:
        before = {"name": "商品A"}
        after = {"name": "商品A", "brand": "品牌X"}
        diffs = _diff_versions(before, after)
        assert len(diffs) == 1
        assert diffs[0]["field"] == "brand"
        assert diffs[0]["old_value"] is None
        assert diffs[0]["new_value"] == "品牌X"

    def test_version_field_level_diff_detects_removed_field(self) -> None:
        before = {"name": "商品A", "brand": "品牌X"}
        after = {"name": "商品A"}
        diffs = _diff_versions(before, after)
        assert len(diffs) == 1
        assert diffs[0]["field"] == "brand"
        assert diffs[0]["old_value"] == "品牌X"
        assert diffs[0]["new_value"] is None

    def test_version_rollback_restores_previous_snapshot(self) -> None:
        entity_id = uuid4()
        operated_by = uuid4()
        v1_snapshot = self._make_snapshot(name="V1名", price=100)
        v1 = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=entity_id,
            snapshot_after=v1_snapshot,
            operated_by=operated_by,
        )
        v2_snapshot = self._make_snapshot(name="V2名", price=200)
        v2 = MasterDataVersionAggregate.create_update(
            entity_type="group_product",
            entity_id=entity_id,
            version_number=2,
            snapshot_before=v1.snapshot_after,
            snapshot_after=v2_snapshot,
            operated_by=operated_by,
        )
        rollback_version = MasterDataVersionAggregate.create_update(
            entity_type="group_product",
            entity_id=entity_id,
            version_number=3,
            snapshot_before=v2.snapshot_after,
            snapshot_after=v1.snapshot_after,
            operated_by=operated_by,
            reason="回滚至 V1",
        )
        assert rollback_version.version_number == 3
        assert rollback_version.snapshot_after == v1.snapshot_after
        assert rollback_version.snapshot_before == v2.snapshot_after
        assert rollback_version.reason == "回滚至 V1"
        assert rollback_version.change_type == ChangeType.UPDATE

    def test_version_snapshot_immutability_via_create_only(self) -> None:
        version = MasterDataVersionAggregate.create_initial(
            entity_type="group_product",
            entity_id=uuid4(),
            snapshot_after={"name": "商品A"},
            operated_by=uuid4(),
        )
        assert version.snapshot_after == {"name": "商品A"}
        assert version.version_number == 1
        assert version.change_type == ChangeType.CREATE
        assert version.reason is None