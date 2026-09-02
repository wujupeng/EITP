"""Core Freeze 哈希比对校验器。"""

from __future__ import annotations

from uuid import UUID

from app.application.rel.gate_checkers.base_checker import GateChecker, GateResult
from app.domain.rel.enums import GateType
from app.domain.rel.error_codes import RELErrorCode


class CoreFreezeHashComparator(GateChecker):
    """比对当前核心资产哈希与 PROD-001 冻结基线哈希。"""

    def __init__(self, core_freeze_guard: object | None = None) -> None:
        self._core_freeze_guard = core_freeze_guard

    @property
    def gate_type(self) -> GateType:
        return GateType.CORE_FREEZE_HASH

    async def check(self, release_id: UUID, executed_by: str) -> GateResult:
        if self._core_freeze_guard is None:
            return GateResult(
                gate_type=self.gate_type,
                passed=True,
                detail={"note": "core_freeze_guard not configured, skipping"},
            )

        try:
            current_fingerprints = await self._core_freeze_guard.collect_fingerprints()
            baseline_fingerprints = await self._core_freeze_guard.get_baseline_fingerprints()
        except Exception as e:
            return GateResult(
                gate_type=self.gate_type,
                passed=False,
                detail={"error": str(e)},
                error_code=RELErrorCode.GATE_CORE_TAMPERED.value,
                error_message=f"fingerprint collection failed: {e}",
            )

        tampered: list[dict] = []
        for asset_name, expected_hash in baseline_fingerprints.items():
            actual_hash = current_fingerprints.get(asset_name)
            if actual_hash != expected_hash:
                tampered.append({
                    "asset": asset_name,
                    "expected": expected_hash,
                    "actual": actual_hash,
                })

        if tampered:
            return GateResult(
                gate_type=self.gate_type,
                passed=False,
                detail={"tampered_assets": tampered},
                error_code=RELErrorCode.GATE_CORE_TAMPERED.value,
                error_message=f"{len(tampered)} core asset(s) tampered",
            )
        return GateResult(
            gate_type=self.gate_type,
            passed=True,
            detail={"checked": len(baseline_fingerprints), "all_match": True},
        )