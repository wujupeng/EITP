"""PlatformAdminAccessRequestAggregate 聚合根 - 平台管理员访问申请，审批流状态机。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.domain.sec.platform_admin.value_objects.approval_status import ApprovalStatus
from app.interfaces.middleware.error_handler import SECError, SECErrorCode


_VALID_TRANSITIONS: dict[ApprovalStatus, set[ApprovalStatus]] = {
    ApprovalStatus.PENDING: {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED},
    ApprovalStatus.APPROVED: {ApprovalStatus.GRANTED},
    ApprovalStatus.REJECTED: set(),
    ApprovalStatus.GRANTED: {ApprovalStatus.EXPIRED},
    ApprovalStatus.EXPIRED: set(),
}

_DEFAULT_TTL_SECONDS = 7200
_APPLICATION_TIMEOUT_HOURS = 24


@dataclass
class PlatformAdminAccessRequestAggregate:
    request_id: UUID = field(default_factory=uuid4)
    applicant: str = ""
    target_tenant_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    target_data_scope: str = ""
    reason: str = ""
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approver: str = ""
    approved_at: datetime | None = None
    temp_permission_ttl: int = _DEFAULT_TTL_SECONDS
    access_audit_index: str = ""
    tenant_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))

    def __post_init__(self) -> None:
        if not self.reason:
            raise SECError(SECErrorCode.APPLICATION_NOT_AUDITED, "Access reason is required")

    def _transition(self, target: ApprovalStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.approval_status, set()):
            raise SECError(SECErrorCode.PLATFORM_ADMIN_BUSINESS_DATA_DENIED, f"Invalid transition {self.approval_status} → {target}")
        self.approval_status = target

    def submit(self) -> None:
        if self.approval_status != ApprovalStatus.PENDING:
            raise SECError(SECErrorCode.PLATFORM_ADMIN_BUSINESS_DATA_DENIED, "Request already submitted")
        self.applied_at = datetime.now(timezone.utc)

    def approve(self, approver: str) -> None:
        self.approver = approver
        self.approved_at = datetime.now(timezone.utc)
        self._transition(ApprovalStatus.APPROVED)

    def reject(self, approver: str) -> None:
        self.approver = approver
        self.approved_at = datetime.now(timezone.utc)
        self._transition(ApprovalStatus.REJECTED)

    def grant_temp_permission(self) -> None:
        self._transition(ApprovalStatus.GRANTED)

    def expire(self) -> None:
        self._transition(ApprovalStatus.EXPIRED)

    def is_application_timeout(self) -> bool:
        timeout = self.applied_at + timedelta(hours=_APPLICATION_TIMEOUT_HOURS)
        return datetime.now(timezone.utc) > timeout

    def is_temp_permission_expired(self) -> bool:
        if self.approved_at is None:
            return False
        expiry = self.approved_at + timedelta(seconds=self.temp_permission_ttl)
        return datetime.now(timezone.utc) > expiry

    @property
    def is_active(self) -> bool:
        return self.approval_status == ApprovalStatus.GRANTED and not self.is_temp_permission_expired()