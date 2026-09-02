"""REL 封版编排器 - SealOrchestrator。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.rel.aggregates.release_seal_aggregate import ReleaseSealAggregate
from app.domain.rel.enums import SealStatus
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.core_freeze_declaration_repository import (
    CoreFreezeDeclarationRepository,
)
from app.infrastructure.rel.release_seal_repository import ReleaseSealRepository
from app.infrastructure.rel.rollback_plan_repository import RollbackPlanRepository
from app.infrastructure.rel.seal_gate_record_repository import SealGateRecordRepository

logger = get_logger(__name__)


class SealOrchestrator:
    """封版编排器 - 统一编排门禁 + 采集 + 报告 + 签发。

    编排流程：
    1. 创建 ReleaseSealAggregate(REQUESTED)
    2. 执行 6 项门禁 (SealGateExecutor)
    3. 并行采集 14 项资产快照
    4. 汇编回滚方案
    5. 发布冻结声明
    6. 汇编封版报告
    7. 裁决
    8. 等待联合签发
    9. → SEALED
    """

    def __init__(
        self,
        release_repo: ReleaseSealRepository,
        snapshot_repo: AssetSnapshotRepository,
        gate_repo: SealGateRecordRepository,
        freeze_repo: CoreFreezeDeclarationRepository,
        rollback_repo: RollbackPlanRepository,
        gate_executor: Any | None = None,
        snapshot_collector: Any | None = None,
        report_assembler: Any | None = None,
        co_signer: Any | None = None,
    ) -> None:
        self._release_repo = release_repo
        self._snapshot_repo = snapshot_repo
        self._gate_repo = gate_repo
        self._freeze_repo = freeze_repo
        self._rollback_repo = rollback_repo
        self._gate_executor = gate_executor
        self._snapshot_collector = snapshot_collector
        self._report_assembler = report_assembler
        self._co_signer = co_signer

    async def request_seal(
        self,
        release_number: str,
        version: str,
        git_tag: str,
        executed_by: str,
    ) -> ReleaseSealAggregate:
        seal = ReleaseSealAggregate.request_seal(
            release_number=release_number,
            version=version,
            git_tag=git_tag,
        )
        await self._release_repo.save(seal)
        logger.info(
            "seal_requested",
            release_id=str(seal.release_id),
            release_number=release_number,
            version=version,
            executed_by=executed_by,
        )
        return seal

    async def execute_gates(
        self,
        release_id: UUID,
        executed_by: str,
    ) -> ReleaseSealAggregate:
        seal_dict = await self._release_repo.get_by_id(release_id)
        if seal_dict is None:
            raise RELError(RELErrorCode.SEAL_NOT_FOUND, f"release {release_id} not found")
        seal = self._dict_to_aggregate(seal_dict)

        seal = seal.start_gate()
        await self._release_repo.save(seal)

        if self._gate_executor is None:
            raise RELError(RELErrorCode.GATE_BYPASS_FORBIDDEN, "gate executor not configured")

        gate_results = await self._gate_executor.execute(release_id, executed_by)
        all_passed = all(r.get("result") == "PASS" for r in gate_results)

        if not all_passed:
            seal = seal.mark_gate_failed()
            await self._release_repo.save(seal)
            logger.warning("seal_gate_failed", release_id=str(release_id))
            return seal

        seal = seal.start_snapshot()
        await self._release_repo.save(seal)
        logger.info("seal_gate_passed", release_id=str(release_id))
        return seal

    async def collect_snapshots(
        self,
        release_id: UUID,
        collected_by: str,
    ) -> ReleaseSealAggregate:
        seal_dict = await self._release_repo.get_by_id(release_id)
        if seal_dict is None:
            raise RELError(RELErrorCode.SEAL_NOT_FOUND, f"release {release_id} not found")
        seal = self._dict_to_aggregate(seal_dict)

        if seal.seal_status != SealStatus.SNAPSHOT_COLLECTING:
            raise RELError(
                RELErrorCode.SEAL_INVALID_STATE_TRANSITION,
                f"snapshot collection requires SNAPSHOT_COLLECTING state, current={seal.seal_status.value}",
            )

        if self._snapshot_collector is None:
            raise RELError(
                RELErrorCode.ASSET_SNAPSHOT_ARCHIVE_FAILED,
                "snapshot collector not configured",
            )

        try:
            snapshots = await self._snapshot_collector.collect_all(release_id, collected_by)
        except RELError:
            seal = seal.mark_snapshot_failed()
            await self._release_repo.save(seal)
            raise
        except Exception as e:
            seal = seal.mark_snapshot_failed()
            await self._release_repo.save(seal)
            raise RELError(
                RELErrorCode.ASSET_SNAPSHOT_COLLECTION_TIMEOUT,
                f"snapshot collection failed: {e}",
            ) from e

        seal = seal.start_report_assembly()
        await self._release_repo.save(seal)
        logger.info("snapshots_collected", release_id=str(release_id), count=len(snapshots))
        return seal

    async def assemble_report_and_freeze(
        self,
        release_id: UUID,
        executed_by: str,
    ) -> ReleaseSealAggregate:
        seal_dict = await self._release_repo.get_by_id(release_id)
        if seal_dict is None:
            raise RELError(RELErrorCode.SEAL_NOT_FOUND, f"release {release_id} not found")
        seal = self._dict_to_aggregate(seal_dict)

        if seal.seal_status != SealStatus.REPORT_ASSEMBLING:
            raise RELError(
                RELErrorCode.SEAL_INVALID_STATE_TRANSITION,
                f"report assembly requires REPORT_ASSEMBLING state, current={seal.seal_status.value}",
            )

        if self._report_assembler is not None:
            report = await self._report_assembler.assemble(release_id, executed_by)
            seal = seal.set_evidence_hash(report.get("evidence_hash", ""))
            seal = seal.set_core_freeze_hash(report.get("core_freeze_hash", ""))
            seal = seal.set_test_counts(
                report.get("test_total", 0),
                report.get("test_passed", 0),
            )

        seal = seal.pending_co_sign()
        await self._release_repo.save(seal)
        logger.info("report_assembled_pending_co_sign", release_id=str(release_id))
        return seal

    async def co_sign(
        self,
        release_id: UUID,
        releaser: str,
        security_officer: str,
    ) -> ReleaseSealAggregate:
        seal_dict = await self._release_repo.get_by_id(release_id)
        if seal_dict is None:
            raise RELError(RELErrorCode.SEAL_NOT_FOUND, f"release {release_id} not found")
        seal = self._dict_to_aggregate(seal_dict)

        if self._co_signer is not None:
            await self._co_signer.verify(releaser, security_officer)

        seal = seal.co_sign(releaser, security_officer)
        await self._release_repo.save(seal)
        logger.info("seal_final_pass", release_id=str(release_id), releaser=releaser)
        return seal

    async def mark_failed(self, release_id: UUID) -> ReleaseSealAggregate:
        seal_dict = await self._release_repo.get_by_id(release_id)
        if seal_dict is None:
            raise RELError(RELErrorCode.SEAL_NOT_FOUND, f"release {release_id} not found")
        seal = self._dict_to_aggregate(seal_dict)
        seal = seal.mark_failed()
        await self._release_repo.save(seal)
        logger.warning("seal_final_fail", release_id=str(release_id))
        return seal

    def _dict_to_aggregate(self, d: dict) -> ReleaseSealAggregate:
        from app.domain.rel.enums import SealStatus, SealVerdict
        return ReleaseSealAggregate(
            release_id=UUID(str(d["release_id"])),
            release_number=d["release_number"],
            version=d["version"],
            git_tag=d["git_tag"],
            git_commit_sha=d.get("git_commit_sha"),
            seal_status=SealStatus(d["seal_status"]),
            seal_time=d.get("seal_time"),
            verdict=SealVerdict(d["verdict"]) if d.get("verdict") else None,
            signed_by_releaser=d.get("signed_by_releaser"),
            signed_by_security=d.get("signed_by_security"),
            signed_at=d.get("signed_at"),
            core_freeze_baseline_hash=d.get("core_freeze_baseline_hash"),
            test_total_count=d.get("test_total_count"),
            test_passed_count=d.get("test_passed_count"),
            evidence_hash=d.get("evidence_hash"),
            created_at=d.get("created_at", datetime.now(timezone.utc)),
            updated_at=d.get("updated_at", datetime.now(timezone.utc)),
        )