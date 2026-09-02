"""封版最终裁决器 - SealFinalVerdictJudge。"""

from __future__ import annotations

from uuid import UUID

from structlog import get_logger

from app.domain.rel.enums import SealVerdict
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.asset_snapshot_repository import AssetSnapshotRepository
from app.infrastructure.rel.core_freeze_declaration_repository import (
    CoreFreezeDeclarationRepository,
)
from app.infrastructure.rel.seal_gate_record_repository import SealGateRecordRepository

logger = get_logger(__name__)


class SealFinalVerdictJudge:
    """封版最终裁决器 - 综合门禁 + 快照 + 冻结声明 → FINAL_PASS/FINAL_FAIL。"""

    def __init__(
        self,
        gate_repo: SealGateRecordRepository,
        snapshot_repo: AssetSnapshotRepository,
        freeze_repo: CoreFreezeDeclarationRepository,
    ) -> None:
        self._gate_repo = gate_repo
        self._snapshot_repo = snapshot_repo
        self._freeze_repo = freeze_repo

    async def judge(self, release_id: UUID) -> SealVerdict:
        gates = await self._gate_repo.get_by_release(release_id)
        if not gates:
            raise RELError(
                RELErrorCode.SEAL_AUDIT_INVALID,
                "no gate records found",
            )

        all_gates_pass = all(g["gate_result"] == "PASS" for g in gates)
        if not all_gates_pass:
            logger.warning("verdict_fail_gates", release_id=str(release_id))
            return SealVerdict.FINAL_FAIL

        hash_ok = await self._snapshot_repo.verify_hash(release_id)
        if not hash_ok:
            logger.warning("verdict_fail_snapshot_tampered", release_id=str(release_id))
            return SealVerdict.FINAL_FAIL

        declaration = await self._freeze_repo.get_by_release(release_id)
        if declaration is None:
            raise RELError(
                RELErrorCode.FREEZE_DECLARATION_MISSING,
                "core freeze declaration not found",
            )
        if declaration.get("declaration_status") != "EFFECTIVE":
            raise RELError(
                RELErrorCode.FREEZE_DECLARATION_ALREADY_EFFECTIVE,
                f"declaration not EFFECTIVE: {declaration.get('declaration_status')}",
            )

        logger.info("verdict_final_pass", release_id=str(release_id))
        return SealVerdict.FINAL_PASS