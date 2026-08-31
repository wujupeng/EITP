"""Task 分配服务 - 支持自动分配（工作量均衡）与手动分配。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.warehouse.aggregates.wms_task_aggregate import WmsTaskAggregate
from app.domain.warehouse.value_objects.task_priority import TaskPriority
from app.domain.warehouse.value_objects.wms_task_type import WmsTaskType


@dataclass(frozen=True)
class WorkloadInfo:
    """执行人工作量信息 - 用于自动分配均衡。"""
    user_id: UUID
    active_task_count: int
    avg_completion_ms: float


class TaskAssignmentService:
    """Task 分配领域服务 - 支持自动分配与手动分配。

    自动分配：按工作量均衡（active_task_count 最少优先），受 wms.task_auto_assign 配置控制。
    手动分配：指定 assignee_id。
    分配后状态 ASSIGNED，记录分配审计，发布 WmsTaskAssignedEvent。
    """

    @staticmethod
    def manual_assign(task: WmsTaskAggregate, assignee_id: UUID) -> WmsTaskAggregate:
        """手动分配 - 指定执行人。"""
        task.assign(assignee_id)
        return task

    @staticmethod
    def auto_assign(
        task: WmsTaskAggregate,
        candidates: list[WorkloadInfo],
    ) -> WmsTaskAggregate:
        """自动分配 - 按工作量均衡选择执行人。

        选择策略：active_task_count 最少优先，相同时 avg_completion_ms 最少优先。
        """
        if not candidates:
            raise ValueError("无可用执行人候选")

        sorted_candidates = sorted(
            candidates,
            key=lambda c: (c.active_task_count, c.avg_completion_ms),
        )
        best = sorted_candidates[0]
        task.assign(best.user_id)
        return task

    @staticmethod
    def reassign(task: WmsTaskAggregate, new_assignee_id: UUID) -> WmsTaskAggregate:
        """转交重新分配 - ASSIGNED→ASSIGNED。"""
        task.assign(new_assignee_id)
        return task