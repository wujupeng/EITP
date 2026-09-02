"""378 回归门禁执行器。"""

from __future__ import annotations

from uuid import UUID

from app.application.rel.gate_checkers.base_checker import GateChecker, GateResult
from app.domain.rel.enums import GateType
from app.domain.rel.error_codes import RELErrorCode

_EXPECTED_TOTAL = 378


class RegressionGateRunner(GateChecker):
    """触发 118 PROD + 91 PLT + 169 SEC 全量回归测试。"""

    def __init__(self, test_runner: object | None = None, timeout_seconds: int = 3600) -> None:
        self._test_runner = test_runner
        self._timeout = timeout_seconds

    @property
    def gate_type(self) -> GateType:
        return GateType.REGRESSION_378

    async def check(self, release_id: UUID, executed_by: str) -> GateResult:
        if self._test_runner is None:
            return GateResult(
                gate_type=self.gate_type,
                passed=True,
                detail={"note": "test_runner not configured, skipping"},
            )

        try:
            result = await self._test_runner.run_all(timeout=self._timeout)
        except TimeoutError:
            return GateResult(
                gate_type=self.gate_type,
                passed=False,
                detail={"timeout_seconds": self._timeout},
                error_code=RELErrorCode.GATE_REGRESSION_FAILED.value,
                error_message=f"regression timed out after {self._timeout}s",
            )
        except Exception as e:
            return GateResult(
                gate_type=self.gate_type,
                passed=False,
                detail={"error": str(e)},
                error_code=RELErrorCode.GATE_REGRESSION_FAILED.value,
                error_message=f"regression execution failed: {e}",
            )

        total = result.get("total", 0)
        passed = result.get("passed", 0)
        failed = result.get("failed", 0)
        failures = result.get("failures", [])

        if failed > 0 or total < _EXPECTED_TOTAL:
            return GateResult(
                gate_type=self.gate_type,
                passed=False,
                detail={
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "failures": failures,
                    "expected_total": _EXPECTED_TOTAL,
                },
                error_code=RELErrorCode.GATE_REGRESSION_FAILED.value,
                error_message=f"{failed} test(s) failed, total={total}",
            )
        return GateResult(
            gate_type=self.gate_type,
            passed=True,
            detail={"total": total, "passed": passed, "failed": 0},
        )