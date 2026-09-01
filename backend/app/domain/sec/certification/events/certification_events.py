"""认证批次领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class CertificationBatchStartedEvent:
    batch_id: UUID
    matrix_version: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CertificationBatchCompletedEvent:
    batch_id: UUID
    total_items: int
    passed_count: int
    failed_count: int
    unexecutable_count: int
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CertificationItemPassedEvent:
    item_id: str
    batch_id: UUID
    layer: str
    operation: str
    aggregate_root: str


@dataclass(frozen=True)
class CertificationItemFailedEvent:
    item_id: str
    batch_id: UUID
    layer: str
    operation: str
    aggregate_root: str
    failure_reason: str


@dataclass(frozen=True)
class CertificationItemUnexecutableEvent:
    item_id: str
    batch_id: UUID
    layer: str
    operation: str
    aggregate_root: str
    reason: str


@dataclass(frozen=True)
class CertificateIssuedEvent:
    certificate_id: UUID
    cert_number: str
    matrix_version: str
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CertificateRevokedEvent:
    certificate_id: UUID
    reason: str
    revoked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class PlatformAdminAccessRequestedEvent:
    request_id: UUID
    applicant: str
    target_tenant_id: UUID
    reason: str


@dataclass(frozen=True)
class PlatformAdminAccessGrantedEvent:
    request_id: UUID
    approver: str
    temp_permission_ttl: int


@dataclass(frozen=True)
class AuditTamperAttemptEvent:
    audit_id: UUID
    attempted_by: str
    attempted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))