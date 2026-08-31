"""WMS Task 聚合根 - 所有作业的执行载体，状态机受控。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.warehouse.events.task_events import (
    WmsTaskAssignedEvent,
    WmsTaskCancelledEvent,
    WmsTaskClaimedEvent,
    WmsTaskCompletedEvent,
    WmsTaskCreatedEvent,
    WmsTaskFailedEvent,
)
from app.domain.warehouse.value_objects.task_priority import TaskPriority
from app.domain.warehouse.value_objects.wms_task_status import WmsTaskStatus
from app.domain.warehouse.value_objects.wms_task_type import WmsTaskType
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class WmsTaskAggregate(AggregateRoot):
    """WMS 作业任务聚合根 - 状态机 CREATED→ASSIGNED→IN_PROGRESS→COMPLETED/CANCELLED/FAILED。

    Task 是所有作业（Receiving/Putaway/Picking/Transfer/Shipping）的执行载体。
    状态流转受控，非法流转拒绝 EITP_WMS_TASK_INVALID_STATE_TRANSITION。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        task_type: WmsTaskType,
        document_id: UUID,
        document_type: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._task_type = task_type
        self._document_id = document_id
        self._document_type = document_type
        self._priority = priority
        self._idempotency_key = idempotency_key
        self._correlation_id = correlation_id
        self._status = WmsTaskStatus.CREATED
        self._assignee_id: UUID | None = None
        self._inv_transaction_ids: list[UUID] = []
        self._assigned_at: datetime | None = None
        self._started_at: datetime | None = None
        self._completed_at: datetime | None = None
        self._record_event(
            WmsTaskCreatedEvent(
                tenant_id=tenant_id,
                task_id=self._id.value,
                task_type=task_type.value,
                document_id=document_id,
                correlation_id=correlation_id,
            )
        )

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def task_type(self) -> WmsTaskType:
        return self._task_type

    @property
    def document_id(self) -> UUID:
        return self._document_id

    @property
    def document_type(self) -> str:
        return self._document_type

    @property
    def priority(self) -> TaskPriority:
        return self._priority

    @property
    def idempotency_key(self) -> str | None:
        return self._idempotency_key

    @property
    def correlation_id(self) -> str | None:
        return self._correlation_id

    @property
    def status(self) -> WmsTaskStatus:
        return self._status

    @property
    def assignee_id(self) -> UUID | None:
        return self._assignee_id

    @property
    def inv_transaction_ids(self) -> list[UUID]:
        return list(self._inv_transaction_ids)

    @property
    def assigned_at(self) -> datetime | None:
        return self._assigned_at

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    def _require_status(self, *allowed: WmsTaskStatus) -> None:
        if self._status not in allowed:
            raise WMSError(
                WMSErrorCode.TASK_INVALID_STATE_TRANSITION,
                f"任务状态 {self._status.value} 不允许此操作，期望 {', '.join(s.value for s in allowed)}",
                details={
                    "task_id": str(self._id.value),
                    "current_status": self._status.value,
                    "allowed": [s.value for s in allowed],
                },
            )

    def assign(self, assignee_id: UUID) -> None:
        """分配任务给执行人（CREATED→ASSIGNED 或 ASSIGNED→ASSIGNED 转交）。"""
        self._require_status(WmsTaskStatus.CREATED, WmsTaskStatus.ASSIGNED)
        self._assignee_id = assignee_id
        self._status = WmsTaskStatus.ASSIGNED
        self._assigned_at = datetime.now(timezone.utc)
        self._touch()
        self._record_event(
            WmsTaskAssignedEvent(
                tenant_id=self._tenant_id,
                task_id=self._id.value,
                assignee_id=assignee_id,
                correlation_id=self._correlation_id,
            )
        )

    def claim(self, user_id: UUID) -> None:
        """领取任务（ASSIGNED→IN_PROGRESS，校验越权）。"""
        self._require_status(WmsTaskStatus.ASSIGNED)
        if self._assignee_id is not None and self._assignee_id != user_id:
            raise WMSError(
                WMSErrorCode.TASK_ASSIGNMENT_DENIED,
                "非分配人领取任务，越权拒绝",
                details={
                    "task_id": str(self._id.value),
                    "assignee_id": str(self._assignee_id),
                    "claimer_id": str(user_id),
                },
            )
        self._status = WmsTaskStatus.IN_PROGRESS
        self._started_at = datetime.now(timezone.utc)
        self._touch()
        self._record_event(
            WmsTaskClaimedEvent(
                tenant_id=self._tenant_id,
                task_id=self._id.value,
                user_id=user_id,
                correlation_id=self._correlation_id,
            )
        )

    def start(self) -> None:
        """开始执行（ASSIGNED→IN_PROGRESS，不校验越权，系统调用）。"""
        self._require_status(WmsTaskStatus.ASSIGNED)
        self._status = WmsTaskStatus.IN_PROGRESS
        self._started_at = datetime.now(timezone.utc)
        self._touch()

    def complete(self, inv_transaction_ids: list[UUID]) -> None:
        """完成任务（IN_PROGRESS→COMPLETED，回填 inv_transaction_ids）。"""
        self._require_status(WmsTaskStatus.IN_PROGRESS)
        self._inv_transaction_ids = list(inv_transaction_ids)
        self._status = WmsTaskStatus.COMPLETED
        self._completed_at = datetime.now(timezone.utc)
        self._touch()
        duration_ms: float | None = None
        if self._started_at is not None:
            duration_ms = (self._completed_at - self._started_at).total_seconds() * 1000
        self._record_event(
            WmsTaskCompletedEvent(
                tenant_id=self._tenant_id,
                task_id=self._id.value,
                inv_transaction_ids=list(inv_transaction_ids),
                duration_ms=duration_ms,
                correlation_id=self._correlation_id,
            )
        )

    def fail(self, reason: str = "") -> None:
        """任务失败（IN_PROGRESS→FAILED，INV Transaction 失败）。"""
        self._require_status(WmsTaskStatus.IN_PROGRESS)
        self._status = WmsTaskStatus.FAILED
        self._completed_at = datetime.now(timezone.utc)
        self._touch()
        self._record_event(
            WmsTaskFailedEvent(
                tenant_id=self._tenant_id,
                task_id=self._id.value,
                failure_reason=reason,
                correlation_id=self._correlation_id,
            )
        )

    def cancel(self, reason: str = "") -> None:
        """取消任务（CREATED/ASSIGNED/IN_PROGRESS→CANCELLED）。"""
        self._require_status(
            WmsTaskStatus.CREATED,
            WmsTaskStatus.ASSIGNED,
            WmsTaskStatus.IN_PROGRESS,
        )
        self._status = WmsTaskStatus.CANCELLED
        self._completed_at = datetime.now(timezone.utc)
        self._touch()
        self._record_event(
            WmsTaskCancelledEvent(
                tenant_id=self._tenant_id,
                task_id=self._id.value,
                reason=reason,
                correlation_id=self._correlation_id,
            )
        )

    def retry(self) -> None:
        """重试任务（FAILED→CREATED）。"""
        self._require_status(WmsTaskStatus.FAILED)
        self._status = WmsTaskStatus.CREATED
        self._assignee_id = None
        self._inv_transaction_ids = []
        self._assigned_at = None
        self._started_at = None
        self._completed_at = None
        self._touch()