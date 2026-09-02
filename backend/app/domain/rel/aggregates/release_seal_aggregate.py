"""REL 封版聚合根 - ReleaseSealAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.rel.enums import SealStatus, SealVerdict, is_terminal, is_valid_transition
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


@dataclass(frozen=True)
class ReleaseSealAggregate:
    """封版聚合根 - 9 状态机 + append-only 不可变。"""

    release_id: UUID
    release_number: str
    version: str
    git_tag: str
    git_commit_sha: str | None
    seal_status: SealStatus
    seal_time: datetime | None = None
    verdict: SealVerdict | None = None
    signed_by_releaser: str | None = None
    signed_by_security: str | None = None
    signed_at: datetime | None = None
    core_freeze_baseline_hash: str | None = None
    test_total_count: int | None = None
    test_passed_count: int | None = None
    evidence_hash: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def request_seal(
        cls,
        release_number: str,
        version: str,
        git_tag: str,
    ) -> ReleaseSealAggregate:
        return cls(
            release_id=uuid4(),
            release_number=release_number,
            version=version,
            git_tag=git_tag,
            git_commit_sha=None,
            seal_status=SealStatus.REQUESTED,
        )

    def _transition(self, target: SealStatus) -> ReleaseSealAggregate:
        if is_terminal(self.seal_status):
            raise RELError(
                RELErrorCode.SEAL_INVALID_STATE_TRANSITION,
                f"terminal state {self.seal_status.value} cannot transition",
            )
        if not is_valid_transition(self.seal_status, target):
            raise RELError(
                RELErrorCode.SEAL_INVALID_STATE_TRANSITION,
                f"invalid transition {self.seal_status.value} -> {target.value}",
            )
        return dataclass_replace(self, seal_status=target, updated_at=datetime.now(timezone.utc))

    def start_gate(self) -> ReleaseSealAggregate:
        return self._transition(SealStatus.GATE_RUNNING)

    def mark_gate_failed(self) -> ReleaseSealAggregate:
        return self._transition(SealStatus.GATE_FAILED)

    def start_snapshot(self) -> ReleaseSealAggregate:
        return self._transition(SealStatus.SNAPSHOT_COLLECTING)

    def mark_snapshot_failed(self) -> ReleaseSealAggregate:
        return self._transition(SealStatus.SNAPSHOT_FAILED)

    def start_report_assembly(self) -> ReleaseSealAggregate:
        return self._transition(SealStatus.REPORT_ASSEMBLING)

    def pending_co_sign(self) -> ReleaseSealAggregate:
        return self._transition(SealStatus.PENDING_CO_SIGN)

    def co_sign(
        self,
        releaser: str,
        security_officer: str,
    ) -> ReleaseSealAggregate:
        if self.seal_status != SealStatus.PENDING_CO_SIGN:
            raise RELError(
                RELErrorCode.SEAL_INVALID_STATE_TRANSITION,
                f"co_sign requires PENDING_CO_SIGN, current={self.seal_status.value}",
            )
        now = datetime.now(timezone.utc)
        return dataclass_replace(
            self,
            seal_status=SealStatus.SEALED,
            verdict=SealVerdict.FINAL_PASS,
            signed_by_releaser=releaser,
            signed_by_security=security_officer,
            signed_at=now,
            seal_time=now,
            updated_at=now,
        )

    def mark_failed(self) -> ReleaseSealAggregate:
        return self._transition(SealStatus.FAILED)

    def set_git_commit_sha(self, sha: str) -> ReleaseSealAggregate:
        return dataclass_replace(self, git_commit_sha=sha, updated_at=datetime.now(timezone.utc))

    def set_core_freeze_hash(self, hash_value: str) -> ReleaseSealAggregate:
        return dataclass_replace(self, core_freeze_baseline_hash=hash_value, updated_at=datetime.now(timezone.utc))

    def set_test_counts(self, total: int, passed: int) -> ReleaseSealAggregate:
        return dataclass_replace(self, test_total_count=total, test_passed_count=passed, updated_at=datetime.now(timezone.utc))

    def set_evidence_hash(self, hash_value: str) -> ReleaseSealAggregate:
        return dataclass_replace(self, evidence_hash=hash_value, updated_at=datetime.now(timezone.utc))
