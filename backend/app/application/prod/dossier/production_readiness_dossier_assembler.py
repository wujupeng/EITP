"""生产就绪证明书汇编器。"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.application.prod.dossier.nine_questions_answerer import NineQuestionsAnswerer
from app.domain.audit.audit_entry import AuditAction, AuditEntry
from app.domain.prod.dossier.aggregates.production_readiness_dossier_aggregate import (
    ProductionReadinessDossierAggregate,
)
from app.domain.prod.engine.enums import (
    DossierStatus,
    VerificationConclusion,
    VerificationItem,
)
from app.domain.prod.error_codes import PRODErrorCode
from app.domain.prod.exceptions import PRODError

logger = logging.getLogger(__name__)

ALL_VERIFICATION_ITEMS = list(VerificationItem)


class DossierRepositoryProtocol:
    """证明书仓储接口。"""

    async def save(self, dossier: ProductionReadinessDossierAggregate) -> None: ...


class EvidenceLookupProtocol:
    """证据查询接口。"""

    async def get_evidence_hash_by_run_id(self, run_id: UUID) -> str | None: ...

    async def get_conclusion_by_run_id(self, run_id: UUID) -> VerificationConclusion | None: ...


class AuditWriterProtocol:
    """审计写入接口。"""

    async def write(self, entry: AuditEntry) -> None: ...


class ProductionReadinessDossierAssembler:
    """生产就绪证明书汇编器。

    校验前置 → 汇编证据 → 回答 9 问 → 计算聚合哈希 → 写入 → 审计 → 提交签发
    """

    def __init__(
        self,
        dossier_repo: DossierRepositoryProtocol,
        evidence_lookup: EvidenceLookupProtocol,
        audit_writer: AuditWriterProtocol | None = None,
        answerer: NineQuestionsAnswerer | None = None,
    ) -> None:
        self._repo = dossier_repo
        self._evidence_lookup = evidence_lookup
        self._audit_writer = audit_writer
        self._answerer = answerer or NineQuestionsAnswerer()

    async def assemble(
        self,
        tenant_scope: UUID | str,
        run_ids: list[UUID],
        tenant_id: UUID,
        user_id: UUID | None = None,
    ) -> ProductionReadinessDossierAggregate:
        conclusions: dict[VerificationItem, VerificationConclusion] = {}
        evidence_hashes: list[str] = []

        for run_id in run_ids:
            ev_hash = await self._evidence_lookup.get_evidence_hash_by_run_id(run_id)
            if ev_hash is None:
                raise PRODError(
                    PRODErrorCode.DOSSIER_EVIDENCE_MISSING,
                    f"证据缺失: run_id={run_id}",
                )
            evidence_hashes.append(ev_hash)

            conclusion = await self._evidence_lookup.get_conclusion_by_run_id(run_id)
            if conclusion and len(conclusions) < len(ALL_VERIFICATION_ITEMS):
                idx = len(conclusions)
                if idx < len(ALL_VERIFICATION_ITEMS):
                    conclusions[ALL_VERIFICATION_ITEMS[idx]] = conclusion

        for item in ALL_VERIFICATION_ITEMS:
            if item not in conclusions:
                conclusions[item] = VerificationConclusion.INCONCLUSIVE

        all_pass = all(
            conclusions.get(item) == VerificationConclusion.PASS
            for item in ALL_VERIFICATION_ITEMS
        )
        if not all_pass:
            failed = [
                item.value for item in ALL_VERIFICATION_ITEMS
                if conclusions.get(item) != VerificationConclusion.PASS
            ]
            logger.warning("Dossier assembly: not all PASS, failed=%s", failed)

        nine_answers = self._answerer.answer(conclusions)

        aggregate_hash = hashlib.sha256(
            "|".join(evidence_hashes).encode("utf-8")
        ).hexdigest()

        dossier = ProductionReadinessDossierAggregate.create(tenant_scope=tenant_scope)
        dossier = dossier.assemble(
            run_ids=run_ids,
            nine_questions_answers=nine_answers,
            evidence_aggregate_hash=aggregate_hash,
        )
        await self._repo.save(dossier)

        if self._audit_writer:
            entry = AuditEntry.create(
                tenant_id=tenant_id,
                user_id=user_id,
                action=AuditAction.DOSSIER_ASSEMBLED,
                entity_type="readiness_dossier",
                entity_id=str(dossier.dossier_id),
                new_value={
                    "evidence_hash": aggregate_hash,
                    "run_count": len(run_ids),
                },
            )
            await self._audit_writer.write(entry)

        dossier = dossier.submit_for_signing()
        await self._repo.save(dossier)

        logger.info("Dossier assembled: %s, status=%s", dossier.dossier_id, dossier.status.value)
        return dossier