"""生产就绪证明书聚合根 - 状态流转 DRAFT→PENDING_SIGN→SIGNED/INVALID。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.prod.engine.enums import DossierStatus, DossierVerdict
from app.domain.prod.exceptions import PRODError
from app.domain.prod.error_codes import PRODErrorCode


_DOSSIER_TRANSITIONS: dict[DossierStatus, set[DossierStatus]] = {
    DossierStatus.DRAFT: {DossierStatus.PENDING_SIGN, DossierStatus.INVALID},
    DossierStatus.PENDING_SIGN: {DossierStatus.SIGNED, DossierStatus.INVALID},
    DossierStatus.SIGNED: {DossierStatus.INVALID},
    DossierStatus.INVALID: set(),
}


@dataclass(frozen=True)
class ProductionReadinessDossierAggregate:
    """生产就绪证明书聚合根。

    状态流转: DRAFT → PENDING_SIGN → SIGNED / INVALID
    仅允许状态流转，禁止 UPDATE 内容字段，禁止 DELETE。
    """

    dossier_id: UUID
    dossier_number: str
    version: int
    tenant_scope: UUID | str
    verification_run_ids: list[UUID]
    nine_questions_answers: dict
    evidence_aggregate_hash: str
    verdict: DossierVerdict | None
    status: DossierStatus
    signer: str | None
    signed_at: datetime | None
    valid_until: datetime | None
    audit_record_id: UUID | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_scope: UUID | str,
        dossier_number: str = "",
    ) -> ProductionReadinessDossierAggregate:
        now = datetime.now(timezone.utc)
        return cls(
            dossier_id=uuid4(),
            dossier_number=dossier_number or f"DOSSIER-{now.strftime('%Y%m%d%H%M%S')}",
            version=1,
            tenant_scope=tenant_scope,
            verification_run_ids=[],
            nine_questions_answers={},
            evidence_aggregate_hash="",
            verdict=None,
            status=DossierStatus.DRAFT,
            signer=None,
            signed_at=None,
            valid_until=None,
            audit_record_id=None,
            created_at=now,
        )

    def _transition(self, new_status: DossierStatus) -> ProductionReadinessDossierAggregate:
        if new_status not in _DOSSIER_TRANSITIONS.get(self.status, set()):
            raise PRODError(
                PRODErrorCode.DOSSIER_PREREQUISITE_NOT_MET,
                f"非法状态转换: {self.status.value} → {new_status.value}",
            )
        return replace(self, status=new_status)

    def assemble(
        self,
        run_ids: list[UUID],
        nine_questions_answers: dict,
        evidence_aggregate_hash: str,
    ) -> ProductionReadinessDossierAggregate:
        return replace(
            self,
            verification_run_ids=list(run_ids),
            nine_questions_answers=nine_questions_answers,
            evidence_aggregate_hash=evidence_aggregate_hash,
        )

    def submit_for_signing(self) -> ProductionReadinessDossierAggregate:
        return self._transition(DossierStatus.PENDING_SIGN)

    def sign(self, signer: str, valid_until: datetime) -> ProductionReadinessDossierAggregate:
        agg = self._transition(DossierStatus.SIGNED)
        return replace(
            agg,
            signer=signer,
            signed_at=datetime.now(timezone.utc),
            valid_until=valid_until,
            verdict=DossierVerdict.READY,
        )

    def invalidate(self, reason: str) -> ProductionReadinessDossierAggregate:
        agg = self._transition(DossierStatus.INVALID)
        return replace(
            agg,
            verdict=DossierVerdict.NOT_READY,
        )