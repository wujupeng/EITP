"""验证执行引擎 - 统一编排 16 项验证器。"""

from __future__ import annotations

import logging
import time
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.application.prod.engine.core_freeze_guard import CoreFreezeGuard
from app.application.prod.engine.evidence_collector import (
    CollectedEvidence,
    EvidenceCollector,
)
from app.application.prod.engine.evidence_hash_calculator import EvidenceHashCalculator
from app.application.prod.engine.iverifier import (
    IVerifier,
    VerificationConfig,
    VerificationResult,
)
from app.domain.audit.audit_entry import AuditAction, AuditEntry
from app.domain.prod.engine.aggregates.verification_run_aggregate import (
    EvidenceRecord,
    VerificationRunAggregate,
)
from app.domain.prod.engine.enums import (
    ExecutorRole,
    VerificationConclusion,
    VerificationEnvironment,
    VerificationItem,
    VerificationStatus,
)
from app.domain.prod.error_codes import PRODErrorCode
from app.domain.prod.exceptions import PRODError
from app.infrastructure.prod.engine.verification_run_repository import (
    EvidenceRepository,
    VerificationRunRepository,
)

logger = logging.getLogger(__name__)


class AuditWriterProtocol:
    """PLT-001 统一审计写入接口（简化 Protocol）。"""

    async def write(self, entry: AuditEntry) -> None: ...


class VerificationExecutionEngine:
    """验证执行引擎。

    流程:
    1. CoreFreezeGuard 验证前校验
    2. 创建 VerificationRun (PENDING)
    3. 写入审计 (VERIFICATION_STARTED)
    4. 状态 → RUNNING
    5. 分发至对应 Verifier
    6. Verifier.execute(config)
    7. 证据采集
    8. 状态流转 → COMPLETED/FAILED/INCONCLUSIVE
    9. 写入审计 (VERIFICATION_COMPLETED/FAILED)
    10. CoreFreezeGuard 验证后校验
    """

    def __init__(
        self,
        run_repository: VerificationRunRepository,
        evidence_repository: EvidenceRepository,
        evidence_collector: EvidenceCollector,
        core_freeze_guard: CoreFreezeGuard,
        audit_writer: AuditWriterProtocol | None = None,
        verifiers: dict[VerificationItem, IVerifier] | None = None,
    ) -> None:
        self._run_repo = run_repository
        self._evidence_repo = evidence_repository
        self._evidence_collector = evidence_collector
        self._freeze_guard = core_freeze_guard
        self._audit_writer = audit_writer
        self._verifiers: dict[VerificationItem, IVerifier] = verifiers or {}

    def register_verifier(self, verifier: IVerifier) -> None:
        self._verifiers[verifier.item] = verifier

    async def execute(
        self,
        tenant_id: UUID,
        verification_item: VerificationItem,
        executor: ExecutorRole,
        environment: VerificationEnvironment,
        config_parameters: dict[str, Any],
        user_id: UUID | None = None,
        ip_address: str | None = None,
    ) -> VerificationRunAggregate:
        trace_id = str(uuid_mod.uuid4())

        violations = await self._freeze_guard.verify_before()
        if violations:
            detail = CoreFreezeGuard.violations_to_detail(violations)
            logger.error("Core freeze violated before %s", verification_item.value)

        run = VerificationRunAggregate.create(
            tenant_id=tenant_id,
            verification_item=verification_item,
            executor=executor,
            environment=environment,
            config_snapshot={
                "parameters": config_parameters,
                "environment": environment.value,
            },
            trace_id=trace_id,
        )
        await self._run_repo.save(run)

        if violations:
            run = run.fail(
                PRODErrorCode.CORE_FREEZE_VIOLATED.value,
                detail,
            )
            await self._run_repo.save(run)
            await self._write_audit(
                tenant_id, user_id, ip_address,
                AuditAction.VERIFICATION_FAILED,
                "verification_run", str(run.run_id),
                None, {"item": verification_item.value, "reason": "core_freeze_violated"},
            )
            return run

        await self._write_audit(
            tenant_id, user_id, ip_address,
            AuditAction.VERIFICATION_STARTED,
            "verification_run", str(run.run_id),
            None, {"item": verification_item.value, "trace_id": trace_id},
        )

        run = run.start()
        await self._run_repo.save(run)

        verifier = self._verifiers.get(verification_item)
        if verifier is None:
            run = run.fail(
                PRODErrorCode.VERIFICATION_PREREQUISITE_NOT_MET.value,
                {"reason": f"no verifier registered for {verification_item.value}"},
            )
            await self._run_repo.save(run)
            return run

        config = VerificationConfig(
            verification_item=verification_item,
            tenant_id=tenant_id,
            environment=environment.value,
            parameters=config_parameters,
        )

        start_ts = time.monotonic()
        try:
            result: VerificationResult = await verifier.execute(config)
        except PRODError as exc:
            result = VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report={"error": exc.message},
                failure_code=exc.code.value,
                failure_detail=exc.details,
            )
        except Exception as exc:
            result = VerificationResult(
                conclusion=VerificationConclusion.FAIL,
                report={"error": str(exc)},
                failure_code=PRODErrorCode.INTERNAL_ERROR.value,
                failure_detail={"exception_type": type(exc).__name__},
            )
        duration_ms = int((time.monotonic() - start_ts) * 1000)

        run = run.enter_evidence_collecting()
        await self._run_repo.save(run)

        collected = await self._evidence_collector.collect(
            run_id=run.run_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            report=result.report,
        )

        for ev_type, ev_path, ev_hash, ev_size in [
            ("REPORT", collected.report_path, collected.triplet.report_hash, collected.report_size),
            ("METRICS_SNAPSHOT", collected.metrics_snapshot_path, collected.triplet.metrics_snapshot_hash, collected.metrics_size),
            ("LOG", collected.log_path, collected.triplet.log_hash, collected.log_size),
        ]:
            evidence = EvidenceRecord.create(
                run_id=run.run_id,
                tenant_id=tenant_id,
                evidence_type=ev_type,
                storage_path=ev_path,
                content_hash=ev_hash,
                size_bytes=ev_size,
                trace_id=trace_id,
            )
            await self._evidence_repo.save(evidence)

        aggregate_hash = collected.triplet.aggregate_hash

        if result.conclusion == VerificationConclusion.PASS:
            run = run.complete(
                evidence_hash=aggregate_hash,
                evidence_report_path=collected.report_path,
                evidence_metrics_snapshot_path=collected.metrics_snapshot_path,
                evidence_log_path=collected.log_path,
            )
            audit_action = AuditAction.VERIFICATION_COMPLETED
        elif result.conclusion == VerificationConclusion.INCONCLUSIVE:
            run = run.mark_inconclusive(
                result.failure_detail.get("reason", "inconclusive") if result.failure_detail else "inconclusive"
            )
            audit_action = AuditAction.VERIFICATION_FAILED
        else:
            run = run.fail(
                result.failure_code or PRODErrorCode.INTERNAL_ERROR.value,
                result.failure_detail or {},
            )
            audit_action = AuditAction.VERIFICATION_FAILED

        await self._run_repo.save(run)

        await self._write_audit(
            tenant_id, user_id, ip_address,
            AuditAction.EVIDENCE_COLLECTED,
            "verification_run", str(run.run_id),
            None, {"evidence_hash": aggregate_hash, "trace_id": trace_id},
        )

        await self._write_audit(
            tenant_id, user_id, ip_address,
            audit_action,
            "verification_run", str(run.run_id),
            None, {
                "item": verification_item.value,
                "conclusion": run.conclusion.value if run.conclusion else None,
                "duration_ms": duration_ms,
            },
        )

        post_violations = await self._freeze_guard.verify_after()
        if post_violations:
            logger.error(
                "Core freeze violated after %s: %d violations",
                verification_item.value,
                len(post_violations),
            )

        return run

    async def _write_audit(
        self,
        tenant_id: UUID,
        user_id: UUID | None,
        ip_address: str | None,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        old_value: dict | None,
        new_value: dict | None,
    ) -> None:
        if self._audit_writer is None:
            return
        entry = AuditEntry.create(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
        )
        await self._audit_writer.write(entry)