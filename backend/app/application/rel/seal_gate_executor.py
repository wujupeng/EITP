"""REL 封版门禁执行器 - SealGateExecutor。"""

from __future__ import annotations

from structlog import get_logger
from uuid import UUID

from app.application.rel.gate_checkers.base_checker import GateChecker, GateResult
from app.domain.rel.aggregates.seal_gate_record_aggregate import SealGateRecordAggregate
from app.domain.rel.enums import GateType
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError
from app.infrastructure.rel.seal_gate_record_repository import SealGateRecordRepository

logger = get_logger(__name__)


class SealGateExecutor:
    """门禁执行器 - 串行执行 6 项门禁，任一失败阻断。"""

    def __init__(
        self,
        gate_repository: SealGateRecordRepository,
        checkers: list[GateChecker],
    ) -> None:
        self._gate_repo = gate_repository
        self._checkers = checkers
        if len(checkers) != 6:
            raise RELError(
                RELErrorCode.GATE_BYPASS_FORBIDDEN,
                f"exactly 6 gate checkers required, got {len(checkers)}",
            )

    async def execute(
        self,
        release_id: UUID,
        executed_by: str,
    ) -> list[dict]:
        results: list[dict] = []
        for checker in self._checkers:
            gate_result = await checker.check(release_id, executed_by)

            record = SealGateRecordAggregate.create(
                release_id=release_id,
                gate_type=checker.gate_type,
                gate_result="PASS" if gate_result.passed else "FAIL",
                gate_detail={
                    "detail": gate_result.detail,
                    "error_code": gate_result.error_code,
                    "error_message": gate_result.error_message,
                },
                executed_by=executed_by,
            )
            await self._gate_repo.save(record)

            results.append({
                "gate_type": checker.gate_type.value,
                "result": "PASS" if gate_result.passed else "FAIL",
                "detail": gate_result.detail,
                "error_code": gate_result.error_code,
                "error_message": gate_result.error_message,
            })

            logger.info(
                "gate_executed",
                release_id=str(release_id),
                gate_type=checker.gate_type.value,
                result="PASS" if gate_result.passed else "FAIL",
            )

            if not gate_result.passed:
                logger.warning(
                    "gate_failed_blocking",
                    release_id=str(release_id),
                    gate_type=checker.gate_type.value,
                    error_code=gate_result.error_code,
                )
                break

        return results

    async def retry_gates(
        self,
        release_id: UUID,
        gate_types: list[GateType],
        executed_by: str,
    ) -> list[dict]:
        checker_map = {c.gate_type: c for c in self._checkers}
        results: list[dict] = []
        for gt in gate_types:
            checker = checker_map.get(gt)
            if checker is None:
                continue
            gate_result = await checker.check(release_id, executed_by)
            record = SealGateRecordAggregate.create(
                release_id=release_id,
                gate_type=checker.gate_type,
                gate_result="PASS" if gate_result.passed else "FAIL",
                gate_detail={
                    "detail": gate_result.detail,
                    "error_code": gate_result.error_code,
                    "error_message": gate_result.error_message,
                    "retry": True,
                },
                executed_by=executed_by,
            )
            await self._gate_repo.save(record)
            results.append({
                "gate_type": checker.gate_type.value,
                "result": "PASS" if gate_result.passed else "FAIL",
                "detail": gate_result.detail,
                "retry": True,
            })
        return results