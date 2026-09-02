"""验证执行聚合根 - append-only 不可篡改，状态机驱动。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.prod.engine.enums import (
    VerificationConclusion,
    VerificationEnvironment,
    VerificationItem,
    VerificationStatus,
    ExecutorRole,
)
from app.domain.prod.exceptions import PRODError
from app.domain.prod.error_codes import PRODErrorCode


_ALLOWED_TRANSITIONS: dict[VerificationStatus, set[VerificationStatus]] = {
    VerificationStatus.PENDING: {
        VerificationStatus.RUNNING,
        VerificationStatus.FAILED,
    },
    VerificationStatus.RUNNING: {
        VerificationStatus.EVIDENCE_COLLECTING,
        VerificationStatus.FAILED,
        VerificationStatus.INCONCLUSIVE,
    },
    VerificationStatus.EVIDENCE_COLLECTING: {
        VerificationStatus.COMPLETED,
        VerificationStatus.FAILED,
    },
    VerificationStatus.COMPLETED: set(),
    VerificationStatus.FAILED: {VerificationStatus.PENDING},
    VerificationStatus.INCONCLUSIVE: {VerificationStatus.PENDING},
}


@dataclass(frozen=True)
class VerificationRunAggregate:
    """验证执行聚合根 - append-only 不可篡改。

    状态机: PENDING → RUNNING → EVIDENCE_COLLECTING → COMPLETED/FAILED/INCONCLUSIVE
    """

    run_id: UUID
    tenant_id: UUID
    verification_item: VerificationItem
    executor: ExecutorRole
    environment: VerificationEnvironment
    status: VerificationStatus
    started_at: datetime | None
    finished_at: datetime | None
    config_snapshot: dict
    conclusion: VerificationConclusion | None
    evidence_report_path: str | None
    evidence_metrics_snapshot_path: str | None
    evidence_log_path: str | None
    evidence_hash: str | None
    trace_id: str
    failure_detail: dict | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        verification_item: VerificationItem,
        executor: ExecutorRole,
        environment: VerificationEnvironment,
        config_snapshot: dict,
        trace_id: str,
    ) -> VerificationRunAggregate:
        return cls(
            run_id=uuid4(),
            tenant_id=tenant_id,
            verification_item=verification_item,
            executor=executor,
            environment=environment,
            status=VerificationStatus.PENDING,
            started_at=None,
            finished_at=None,
            config_snapshot=config_snapshot,
            conclusion=None,
            evidence_report_path=None,
            evidence_metrics_snapshot_path=None,
            evidence_log_path=None,
            evidence_hash=None,
            trace_id=trace_id,
            failure_detail=None,
            created_at=datetime.now(timezone.utc),
        )

    def _transition(self, new_status: VerificationStatus) -> VerificationRunAggregate:
        if new_status not in _ALLOWED_TRANSITIONS.get(self.status, set()):
            raise PRODError(
                PRODErrorCode.VERIFICATION_PREREQUISITE_NOT_MET,
                f"非法状态转换: {self.status.value} → {new_status.value}",
            )
        return replace(self, status=new_status)

    def start(self) -> VerificationRunAggregate:
        return self._transition(VerificationStatus.RUNNING)._with(
            started_at=datetime.now(timezone.utc)
        )

    def enter_evidence_collecting(self) -> VerificationRunAggregate:
        return self._transition(VerificationStatus.EVIDENCE_COLLECTING)

    def complete(
        self,
        evidence_hash: str,
        evidence_report_path: str,
        evidence_metrics_snapshot_path: str,
        evidence_log_path: str,
    ) -> VerificationRunAggregate:
        agg = self._transition(VerificationStatus.COMPLETED)
        return replace(
            agg,
            conclusion=VerificationConclusion.PASS,
            finished_at=datetime.now(timezone.utc),
            evidence_hash=evidence_hash,
            evidence_report_path=evidence_report_path,
            evidence_metrics_snapshot_path=evidence_metrics_snapshot_path,
            evidence_log_path=evidence_log_path,
        )

    def fail(
        self,
        error_code: str,
        detail: dict,
    ) -> VerificationRunAggregate:
        agg = self._transition(VerificationStatus.FAILED)
        return replace(
            agg,
            conclusion=VerificationConclusion.FAIL,
            finished_at=datetime.now(timezone.utc),
            failure_detail={"error_code": error_code, "detail": detail},
        )

    def mark_inconclusive(self, reason: str) -> VerificationRunAggregate:
        agg = self._transition(VerificationStatus.INCONCLUSIVE)
        return replace(
            agg,
            conclusion=VerificationConclusion.INCONCLUSIVE,
            finished_at=datetime.now(timezone.utc),
            failure_detail={"reason": reason},
        )

    def retry(self) -> VerificationRunAggregate:
        agg = self._transition(VerificationStatus.PENDING)
        return replace(
            agg,
            started_at=None,
            finished_at=None,
            conclusion=None,
            evidence_hash=None,
            evidence_report_path=None,
            evidence_metrics_snapshot_path=None,
            evidence_log_path=None,
            failure_detail=None,
        )

    def _with(self, **kwargs) -> VerificationRunAggregate:
        return replace(self, **kwargs)


@dataclass(frozen=True)
class EvidenceRecord:
    """证据记录 - 证据三元组中的单条证据。"""

    evidence_id: UUID
    run_id: UUID
    tenant_id: UUID
    evidence_type: str
    storage_path: str
    content_hash: str
    size_bytes: int
    trace_id: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        run_id: UUID,
        tenant_id: UUID,
        evidence_type: str,
        storage_path: str,
        content_hash: str,
        size_bytes: int,
        trace_id: str,
    ) -> EvidenceRecord:
        return cls(
            evidence_id=uuid4(),
            run_id=run_id,
            tenant_id=tenant_id,
            evidence_type=evidence_type,
            storage_path=storage_path,
            content_hash=content_hash,
            size_bytes=size_bytes,
            trace_id=trace_id,
            created_at=datetime.now(timezone.utc),
        )