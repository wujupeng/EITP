"""里程碑 FINAL PASS 校验器 - 校验 10 里程碑全部 FINAL PASS。"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.application.rel.gate_checkers.base_checker import GateChecker, GateResult
from app.domain.rel.enums import GateType
from app.domain.rel.error_codes import RELErrorCode

_MILESTONES = [
    "eitp_mt_001",
    "eitp_iam_001",
    "eitp_inv_001",
    "eitp_mdm_001",
    "eitp_wms_001",
    "eitp_pur_001",
    "eitp_sal_001",
    "eitp_sec_001",
    "eitp_plt_001",
    "eitp_prod_001",
]


class MilestoneFinalPassChecker(GateChecker):
    """校验 10 里程碑评审报告全部 FINAL PASS。"""

    def __init__(self, specs_root: str) -> None:
        self._specs_root = Path(specs_root)

    @property
    def gate_type(self) -> GateType:
        return GateType.MILESTONE_FINAL_PASS

    async def check(self, release_id: UUID, executed_by: str) -> GateResult:
        not_passed: list[str] = []
        for ms in _MILESTONES:
            review_path = self._specs_root / ms / "review.md"
            if not review_path.exists():
                not_passed.append(f"{ms}: review.md not found")
                continue
            content = review_path.read_text(encoding="utf-8")
            if "FINAL PASS" not in content:
                not_passed.append(f"{ms}: not FINAL PASS")

        if not_passed:
            return GateResult(
                gate_type=self.gate_type,
                passed=False,
                detail={"failed_milestones": not_passed},
                error_code=RELErrorCode.GATE_MILESTONE_NOT_PASS.value,
                error_message=f"{len(not_passed)} milestone(s) not FINAL PASS",
            )
        return GateResult(
            gate_type=self.gate_type,
            passed=True,
            detail={"checked": len(_MILESTONES), "all_final_pass": True},
        )