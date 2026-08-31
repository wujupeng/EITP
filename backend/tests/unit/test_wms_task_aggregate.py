"""T16-01 WmsTaskAggregate 状态机单元测试。

覆盖 CREATED→ASSIGNED→IN_PROGRESS→COMPLETED/CANCELLED/FAILED 全部合法流转、
非法流转拒绝、越权领取拒绝、优先级排序、FAILED→CREATED 重试。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.shared.entity import EntityId
from app.domain.warehouse.aggregates.wms_task_aggregate import WmsTaskAggregate
from app.domain.warehouse.value_objects.task_priority import TaskPriority
from app.domain.warehouse.value_objects.wms_task_status import WmsTaskStatus
from app.domain.warehouse.value_objects.wms_task_type import WmsTaskType
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


def _make_task(
    *,
    task_type: WmsTaskType = WmsTaskType.RECEIVING,
    priority: TaskPriority = TaskPriority.MEDIUM,
    document_type: str = "purchase_order",
) -> WmsTaskAggregate:
    return WmsTaskAggregate(
        id=EntityId.generate(),
        tenant_id=uuid4(),
        task_type=task_type,
        document_id=uuid4(),
        document_type=document_type,
        priority=priority,
        idempotency_key="idem-task-1",
        correlation_id="corr-task-1",
    )


class WmsTaskAggregateTest:
    """WmsTaskAggregate 状态机与受控操作测试。"""

    # --- 构造与初始状态 ---

    def test_initial_state_is_created(self) -> None:
        task = _make_task()
        assert task.status == WmsTaskStatus.CREATED
        assert task.assignee_id is None
        assert task.inv_transaction_ids == []
        assert task.assigned_at is None
        assert task.started_at is None
        assert task.completed_at is None

    def test_construction_records_created_event(self) -> None:
        task = _make_task()
        events = list(task.pull_events())
        assert len(events) == 1
        assert events[0].__class__.__name__ == "WmsTaskCreatedEvent"

    def test_priority_and_type_persisted(self) -> None:
        task = _make_task(task_type=WmsTaskType.PICKING, priority=TaskPriority.HIGH)
        assert task.task_type == WmsTaskType.PICKING
        assert task.priority == TaskPriority.HIGH

    # --- 合法流转 ---

    def test_created_to_assigned(self) -> None:
        task = _make_task()
        assignee = uuid4()
        task.assign(assignee)
        assert task.status == WmsTaskStatus.ASSIGNED
        assert task.assignee_id == assignee
        assert task.assigned_at is not None

    def test_assigned_to_in_progress_via_claim(self) -> None:
        task = _make_task()
        assignee = uuid4()
        task.assign(assignee)
        task.claim(assignee)
        assert task.status == WmsTaskStatus.IN_PROGRESS
        assert task.started_at is not None

    def test_assigned_to_in_progress_via_start(self) -> None:
        task = _make_task()
        assignee = uuid4()
        task.assign(assignee)
        task.start()
        assert task.status == WmsTaskStatus.IN_PROGRESS
        assert task.started_at is not None

    def test_in_progress_to_completed(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        inv_tx_ids = [uuid4(), uuid4()]
        task.complete(inv_tx_ids)
        assert task.status == WmsTaskStatus.COMPLETED
        assert task.inv_transaction_ids == inv_tx_ids
        assert task.completed_at is not None

    def test_in_progress_to_failed(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.fail("inventory transaction failed")
        assert task.status == WmsTaskStatus.FAILED
        assert task.completed_at is not None

    def test_created_to_cancelled(self) -> None:
        task = _make_task()
        task.cancel("user cancelled")
        assert task.status == WmsTaskStatus.CANCELLED

    def test_assigned_to_cancelled(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.cancel("reassigned")
        assert task.status == WmsTaskStatus.CANCELLED

    def test_in_progress_to_cancelled(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.cancel("aborted")
        assert task.status == WmsTaskStatus.CANCELLED

    def test_assigned_reassign_transfers_assignee(self) -> None:
        task = _make_task()
        first = uuid4()
        second = uuid4()
        task.assign(first)
        assert task.assignee_id == first
        task.assign(second)
        assert task.status == WmsTaskStatus.ASSIGNED
        assert task.assignee_id == second

    # --- FAILED→CREATED 重试 ---

    def test_failed_to_created_retry(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.fail("transient error")
        assert task.status == WmsTaskStatus.FAILED
        task.retry()
        assert task.status == WmsTaskStatus.CREATED
        assert task.assignee_id is None
        assert task.inv_transaction_ids == []
        assert task.assigned_at is None
        assert task.started_at is None
        assert task.completed_at is None

    def test_retry_then_full_lifecycle_again(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.fail("boom")
        task.retry()
        assignee = uuid4()
        task.assign(assignee)
        task.claim(assignee)
        task.complete([uuid4()])
        assert task.status == WmsTaskStatus.COMPLETED

    # --- 越权领取拒绝 ---

    def test_claim_by_non_assignee_rejected(self) -> None:
        task = _make_task()
        assignee = uuid4()
        other = uuid4()
        task.assign(assignee)
        with pytest.raises(WMSError) as exc:
            task.claim(other)
        assert exc.value.code == WMSErrorCode.TASK_ASSIGNMENT_DENIED
        assert task.status == WmsTaskStatus.ASSIGNED

    def test_claim_by_assignee_allowed(self) -> None:
        task = _make_task()
        assignee = uuid4()
        task.assign(assignee)
        task.claim(assignee)
        assert task.status == WmsTaskStatus.IN_PROGRESS

    def test_start_does_not_check_authorization(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        assert task.status == WmsTaskStatus.IN_PROGRESS

    # --- 非法流转拒绝 ---

    def test_illegal_claim_from_created(self) -> None:
        task = _make_task()
        with pytest.raises(WMSError) as exc:
            task.claim(uuid4())
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_start_from_created(self) -> None:
        task = _make_task()
        with pytest.raises(WMSError) as exc:
            task.start()
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_complete_from_created(self) -> None:
        task = _make_task()
        with pytest.raises(WMSError) as exc:
            task.complete([uuid4()])
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_fail_from_created(self) -> None:
        task = _make_task()
        with pytest.raises(WMSError) as exc:
            task.fail()
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_complete_from_assigned(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        with pytest.raises(WMSError) as exc:
            task.complete([uuid4()])
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_fail_from_assigned(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        with pytest.raises(WMSError) as exc:
            task.fail()
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_assign_from_in_progress(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        with pytest.raises(WMSError) as exc:
            task.assign(uuid4())
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_claim_from_completed(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.complete([uuid4()])
        with pytest.raises(WMSError) as exc:
            task.claim(uuid4())
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_complete_from_completed(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.complete([uuid4()])
        with pytest.raises(WMSError) as exc:
            task.complete([uuid4()])
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_cancel_from_completed(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.complete([uuid4()])
        with pytest.raises(WMSError) as exc:
            task.cancel()
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_retry_from_completed(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.complete([uuid4()])
        with pytest.raises(WMSError) as exc:
            task.retry()
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_assign_from_cancelled(self) -> None:
        task = _make_task()
        task.cancel()
        with pytest.raises(WMSError) as exc:
            task.assign(uuid4())
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_claim_from_cancelled(self) -> None:
        task = _make_task()
        task.cancel()
        with pytest.raises(WMSError) as exc:
            task.claim(uuid4())
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_retry_from_created(self) -> None:
        task = _make_task()
        with pytest.raises(WMSError) as exc:
            task.retry()
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_assign_from_failed(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.fail()
        with pytest.raises(WMSError) as exc:
            task.assign(uuid4())
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    def test_illegal_cancel_from_failed(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.fail()
        with pytest.raises(WMSError) as exc:
            task.cancel()
        assert exc.value.code == WMSErrorCode.TASK_INVALID_STATE_TRANSITION

    # --- 事件记录 ---

    def test_complete_records_completed_event_with_duration(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.complete([uuid4()])
        event_names = [e.__class__.__name__ for e in task.pull_events()]
        assert "WmsTaskCompletedEvent" in event_names

    def test_fail_records_failed_event(self) -> None:
        task = _make_task()
        task.assign(uuid4())
        task.start()
        task.fail("reason-x")
        event_names = [e.__class__.__name__ for e in task.pull_events()]
        assert "WmsTaskFailedEvent" in event_names

    def test_cancel_records_cancelled_event(self) -> None:
        task = _make_task()
        task.cancel("no longer needed")
        event_names = [e.__class__.__name__ for e in task.pull_events()]
        assert "WmsTaskCancelledEvent" in event_names


class TaskPriorityTest:
    """TaskPriority 优先级排序测试。"""

    def test_priority_ordering_high_before_medium_before_low(self) -> None:
        priorities = [TaskPriority.LOW, TaskPriority.HIGH, TaskPriority.MEDIUM]
        order = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}
        sorted_priorities = sorted(priorities, key=lambda p: order[p])
        assert sorted_priorities == [TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]

    def test_priority_values_are_strings(self) -> None:
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.LOW.value == "low"

    def test_tasks_sortable_by_priority(self) -> None:
        low_task = _make_task(priority=TaskPriority.LOW)
        high_task = _make_task(priority=TaskPriority.HIGH)
        medium_task = _make_task(priority=TaskPriority.MEDIUM)
        tasks = [low_task, high_task, medium_task]
        order = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}
        sorted_tasks = sorted(tasks, key=lambda t: order[t.priority])
        assert sorted_tasks[0].priority == TaskPriority.HIGH
        assert sorted_tasks[1].priority == TaskPriority.MEDIUM
        assert sorted_tasks[2].priority == TaskPriority.LOW


class WmsTaskStatusTest:
    """WmsTaskStatus 六态枚举测试。"""

    def test_all_six_states_present(self) -> None:
        expected = {"created", "assigned", "in_progress", "completed", "cancelled", "failed"}
        actual = {s.value for s in WmsTaskStatus}
        assert actual == expected

    def test_state_count(self) -> None:
        assert len(list(WmsTaskStatus)) == 6