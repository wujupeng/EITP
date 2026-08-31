"""治理工作流聚合根 - 主数据变更治理工作流。

集团级治理（tenant_id 为空）由集团主数据管理员发起、集团审批人审批。
企业级治理（含 tenant_id）由企业主数据管理员发起、企业审批人审批。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

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
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class GovernanceLevel(str, Enum):
    GROUP = "group"
    ENTERPRISE = "enterprise"


class GovernanceWorkflowAggregate(AggregateRoot):
    """治理工作流聚合根 - 编排主数据变更审批流程。"""

    def __init__(
        self,
        id: EntityId,
        governance_level: GovernanceLevel,
        entity_type: str,
        target_version_id: UUID,
        tenant_id: UUID | None = None,
        entity_id: UUID | None = None,
        status: GovernanceState = GovernanceState.DRAFT,
        submitted_by: UUID | None = None,
        submitted_at: datetime | None = None,
        approved_by: UUID | None = None,
        approved_at: datetime | None = None,
        approval_opinion: str | None = None,
        published_by: UUID | None = None,
        published_at: datetime | None = None,
        rollback_by: UUID | None = None,
        rollback_at: datetime | None = None,
        rollback_reason: str | None = None,
    ) -> None:
        super().__init__(id)
        if governance_level == GovernanceLevel.GROUP and tenant_id is not None:
            raise MDMError(
                MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION,
                "集团级治理工作流不能含 tenant_id",
            )
        if governance_level == GovernanceLevel.ENTERPRISE and tenant_id is None:
            raise MDMError(
                MDMErrorCode.INVALID_GOVERNANCE_STATE_TRANSITION,
                "企业级治理工作流必须含 tenant_id",
            )
        self._governance_level = governance_level
        self._entity_type = entity_type
        self._target_version_id = target_version_id
        self._tenant_id = tenant_id
        self._entity_id = entity_id
        self._status = status
        self._submitted_by = submitted_by
        self._submitted_at = submitted_at
        self._approved_by = approved_by
        self._approved_at = approved_at
        self._approval_opinion = approval_opinion
        self._published_by = published_by
        self._published_at = published_at
        self._rollback_by = rollback_by
        self._rollback_at = rollback_at
        self._rollback_reason = rollback_reason

    @property
    def governance_level(self) -> GovernanceLevel:
        return self._governance_level

    @property
    def entity_type(self) -> str:
        return self._entity_type

    @property
    def target_version_id(self) -> UUID:
        return self._target_version_id

    @property
    def tenant_id(self) -> UUID | None:
        return self._tenant_id

    @property
    def entity_id(self) -> UUID | None:
        return self._entity_id

    @property
    def status(self) -> GovernanceState:
        return self._status

    @property
    def submitted_by(self) -> UUID | None:
        return self._submitted_by

    @property
    def submitted_at(self) -> datetime | None:
        return self._submitted_at

    @property
    def approved_by(self) -> UUID | None:
        return self._approved_by

    @property
    def approved_at(self) -> datetime | None:
        return self._approved_at

    @property
    def approval_opinion(self) -> str | None:
        return self._approval_opinion

    @property
    def published_by(self) -> UUID | None:
        return self._published_by

    @property
    def published_at(self) -> datetime | None:
        return self._published_at

    @property
    def rollback_by(self) -> UUID | None:
        return self._rollback_by

    @property
    def rollback_at(self) -> datetime | None:
        return self._rollback_at

    @property
    def rollback_reason(self) -> str | None:
        return self._rollback_reason

    def is_editable(self) -> bool:
        """已提交变更申请不可修改内容（spec 5.6.1.3）。"""
        return is_editable(self._status)

    def is_group_level(self) -> bool:
        return self._governance_level == GovernanceLevel.GROUP

    def submit(self, submitted_by: UUID) -> None:
        """提交治理申请（DRAFT → SUBMITTED）。"""
        validate_state_transition(self._status, GovernanceState.SUBMITTED)
        self._status = GovernanceState.SUBMITTED
        self._submitted_by = submitted_by
        self._submitted_at = datetime.now(timezone.utc)
        self._touch()
        self._record_event(
            GovernanceRequestSubmittedEvent(
                tenant_id=self._tenant_id,
                request_id=self._id.value,
                governance_level=self._governance_level.value,
                entity_type=self._entity_type,
                entity_id=self._entity_id,
                submitted_by=submitted_by,
            )
        )

    def approve(self, approver: UUID, opinion: str) -> None:
        """审批通过（SUBMITTED → APPROVED）。"""
        validate_state_transition(self._status, GovernanceState.APPROVED)
        self._status = GovernanceState.APPROVED
        self._approved_by = approver
        self._approved_at = datetime.now(timezone.utc)
        self._approval_opinion = opinion
        self._touch()
        self._record_event(
            GovernanceRequestApprovedEvent(
                tenant_id=self._tenant_id,
                request_id=self._id.value,
                governance_level=self._governance_level.value,
                approved_by=approver,
                approval_opinion=opinion,
            )
        )

    def reject(self, rejecter: UUID, opinion: str) -> None:
        """审批拒绝（SUBMITTED → REJECTED）。"""
        validate_state_transition(self._status, GovernanceState.REJECTED)
        self._status = GovernanceState.REJECTED
        self._approved_by = rejecter
        self._approved_at = datetime.now(timezone.utc)
        self._approval_opinion = opinion
        self._touch()
        self._record_event(
            GovernanceRequestRejectedEvent(
                tenant_id=self._tenant_id,
                request_id=self._id.value,
                governance_level=self._governance_level.value,
                rejected_by=rejecter,
                rejection_opinion=opinion,
            )
        )

    def publish(self, published_by: UUID) -> None:
        """发布（APPROVED → PUBLISHED）。"""
        validate_state_transition(self._status, GovernanceState.PUBLISHED)
        self._status = GovernanceState.PUBLISHED
        self._published_by = published_by
        self._published_at = datetime.now(timezone.utc)
        self._touch()
        self._record_event(
            GovernanceRequestPublishedEvent(
                tenant_id=self._tenant_id,
                request_id=self._id.value,
                governance_level=self._governance_level.value,
                published_by=published_by,
                target_version_id=self._target_version_id,
            )
        )

    def rollback(self, rollback_by: UUID, reason: str) -> None:
        """回滚（PUBLISHED → ROLLED_BACK）。"""
        validate_state_transition(self._status, GovernanceState.ROLLED_BACK)
        self._status = GovernanceState.ROLLED_BACK
        self._rollback_by = rollback_by
        self._rollback_at = datetime.now(timezone.utc)
        self._rollback_reason = reason
        self._touch()
        self._record_event(
            GovernanceRequestRollbackEvent(
                tenant_id=self._tenant_id,
                request_id=self._id.value,
                governance_level=self._governance_level.value,
                rollback_by=rollback_by,
                rollback_reason=reason,
            )
        )