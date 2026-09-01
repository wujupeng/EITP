"""CertificationBatchAggregate 聚合根 - 认证批次。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sec.certification.value_objects.batch_status import BatchStatus
from app.interfaces.middleware.error_handler import SECError, SECErrorCode


@dataclass
class CertificationBatchAggregate:
    batch_id: UUID = field(default_factory=uuid4)
    matrix_version: str = ""
    trigger_source: str = "manual"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: BatchStatus = BatchStatus.PENDING
    tenant_id: UUID = field(default_factory=uuid4)
    total_items: int = 0
    passed_count: int = 0
    failed_count: int = 0
    unexecutable_count: int = 0

    def start(self) -> None:
        if self.status != BatchStatus.PENDING:
            raise SECError(SECErrorCode.CERT_ALREADY_RUNNING, f"Batch {self.batch_id} already started")
        self.status = BatchStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def complete(self, passed: int, failed: int, unexecutable: int) -> None:
        if self.status != BatchStatus.RUNNING:
            raise SECError(SECErrorCode.CERT_ISSUE_FAILED, "Batch not running")
        self.status = BatchStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.passed_count = passed
        self.failed_count = failed
        self.unexecutable_count = unexecutable
        self.total_items = passed + failed + unexecutable

    def fail(self, reason: str) -> None:
        self.status = BatchStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)

    @property
    def pass_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.passed_count / self.total_items

    @property
    def all_passed(self) -> bool:
        return self.status == BatchStatus.COMPLETED and self.failed_count == 0 and self.unexecutable_count == 0