"""CertificationItemAggregate 聚合根 - 认证项，三态状态机 PENDING→EXECUTING→PASS/FAIL/UNEXECUTABLE。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.sec.attack_matrix.value_objects.attack_vector import AttackVector
from app.domain.sec.certification.value_objects.evidence_snapshot import EvidenceSnapshot
from app.domain.sec.certification.value_objects.isolation_layer import (
    Conclusion,
    IsolationLayer,
    NineOperation,
)
from app.interfaces.middleware.error_handler import SECError, SECErrorCode


_ITEM_TIMEOUT_SECONDS = 5.0


@dataclass
class CertificationItemAggregate:
    item_id: str = ""
    batch_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    layer: IsolationLayer = IsolationLayer.API
    operation: NineOperation = NineOperation.SELECT
    aggregate_root: str = ""
    attack_vector: AttackVector | None = None
    expected_behavior: str = ""
    actual_behavior: str = ""
    conclusion: Conclusion = Conclusion.PENDING
    evidence: EvidenceSnapshot | None = None
    executed_at: datetime | None = None
    duration_ms: float = 0.0
    failure_reason: str = ""
    tenant_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))

    def execute(self) -> None:
        if self.conclusion != Conclusion.PENDING:
            raise SECError(SECErrorCode.CERT_ALREADY_RUNNING, f"Item {self.item_id} already executed")
        self.conclusion = Conclusion.EXECUTING
        self.executed_at = datetime.now(timezone.utc)

    def capture_evidence(self, evidence: EvidenceSnapshot) -> None:
        self.evidence = evidence

    def judge(self, actual_behavior: str, duration_ms: float) -> None:
        if self.conclusion != Conclusion.EXECUTING:
            raise SECError(SECErrorCode.CERT_ISSUE_FAILED, "Item not in EXECUTING state")
        self.actual_behavior = actual_behavior
        self.duration_ms = duration_ms
        if duration_ms > _ITEM_TIMEOUT_SECONDS * 1000:
            self.conclusion = Conclusion.FAIL
            self.failure_reason = f"Timeout: {duration_ms}ms > {_ITEM_TIMEOUT_SECONDS * 1000}ms"
            return
        if self.evidence is None or not self.evidence.verify_completeness():
            self.conclusion = Conclusion.FAIL
            self.failure_reason = "Evidence missing or incomplete"
            return
        if actual_behavior == self.expected_behavior:
            self.conclusion = Conclusion.PASS
        else:
            self.conclusion = Conclusion.FAIL
            self.failure_reason = f"Expected '{self.expected_behavior}', got '{actual_behavior}'"

    def mark_unexecutable(self, reason: str) -> None:
        if self.conclusion != Conclusion.EXECUTING:
            raise SECError(SECErrorCode.CERT_ISSUE_FAILED, "Item not in EXECUTING state")
        self.conclusion = Conclusion.UNEXECUTABLE
        self.failure_reason = reason

    @property
    def is_pass(self) -> bool:
        return self.conclusion == Conclusion.PASS

    @property
    def is_fail(self) -> bool:
        return self.conclusion == Conclusion.FAIL

    @property
    def is_unexecutable(self) -> bool:
        return self.conclusion == Conclusion.UNEXECUTABLE