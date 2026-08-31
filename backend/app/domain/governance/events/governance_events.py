"""治理领域事件 - 复用 MT-001 DomainEventBus 异步发布。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class GovernanceDomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: UUID | None = None
    correlation_id: str | None = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


@dataclass(frozen=True)
class GovernanceRequestSubmittedEvent(GovernanceDomainEvent):
    request_id: UUID | None = None
    governance_level: str = ""
    entity_type: str = ""
    entity_id: UUID | None = None
    submitted_by: UUID | None = None
    change_type: str = "submitted"


@dataclass(frozen=True)
class GovernanceRequestApprovedEvent(GovernanceDomainEvent):
    request_id: UUID | None = None
    governance_level: str = ""
    approved_by: UUID | None = None
    approval_opinion: str = ""
    change_type: str = "approved"


@dataclass(frozen=True)
class GovernanceRequestRejectedEvent(GovernanceDomainEvent):
    request_id: UUID | None = None
    governance_level: str = ""
    rejected_by: UUID | None = None
    rejection_opinion: str = ""
    change_type: str = "rejected"


@dataclass(frozen=True)
class GovernanceRequestPublishedEvent(GovernanceDomainEvent):
    request_id: UUID | None = None
    governance_level: str = ""
    published_by: UUID | None = None
    target_version_id: UUID | None = None
    change_type: str = "published"


@dataclass(frozen=True)
class GovernanceRequestRollbackEvent(GovernanceDomainEvent):
    request_id: UUID | None = None
    governance_level: str = ""
    rollback_by: UUID | None = None
    rollback_reason: str = ""
    change_type: str = "rolled_back"