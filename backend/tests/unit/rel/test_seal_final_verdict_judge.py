"""SealFinalVerdictJudge 单元测试 - 最终裁决逻辑 FINAL_PASS/FINAL_FAIL。

覆盖 application/rel/seal_final_verdict_judge.py 的 judge() 综合门禁+快照+冻结声明裁决：
- 无门禁记录 → SEAL_AUDIT_INVALID
- 任一门禁 FAIL → FINAL_FAIL
- 快照哈希校验失败 → FINAL_FAIL
- 冻结声明缺失 → FREEZE_DECLARATION_MISSING
- 冻结声明非 EFFECTIVE → FREEZE_DECLARATION_ALREADY_EFFECTIVE
- 全部通过 → FINAL_PASS
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.rel.seal_final_verdict_judge import SealFinalVerdictJudge
from app.domain.rel.enums import SealVerdict
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


def _make_judge(
    gates: list[dict] | None = None,
    hash_ok: bool = True,
    declaration: dict | None = None,
) -> tuple[SealFinalVerdictJudge, AsyncMock, AsyncMock, AsyncMock]:
    gate_repo = AsyncMock()
    gate_repo.get_by_release = AsyncMock(return_value=gates if gates is not None else [])
    snapshot_repo = AsyncMock()
    snapshot_repo.verify_hash = AsyncMock(return_value=hash_ok)
    freeze_repo = AsyncMock()
    freeze_repo.get_by_release = AsyncMock(return_value=declaration)
    judge = SealFinalVerdictJudge(gate_repo, snapshot_repo, freeze_repo)
    return judge, gate_repo, snapshot_repo, freeze_repo


class SealFinalVerdictJudgeTest:
    """SealFinalVerdictJudge 最终裁决器测试。"""

    async def test_no_gate_records_raises_seal_audit_invalid(self) -> None:
        judge, _, _, _ = _make_judge(gates=[])
        with pytest.raises(RELError) as exc:
            await judge.judge(uuid4())
        assert exc.value.code == RELErrorCode.SEAL_AUDIT_INVALID

    async def test_any_gate_fail_returns_final_fail(self) -> None:
        judge, _, _, _ = _make_judge(
            gates=[
                {"gate_result": "PASS"},
                {"gate_result": "FAIL"},
            ],
            hash_ok=True,
            declaration={"declaration_status": "EFFECTIVE"},
        )
        verdict = await judge.judge(uuid4())
        assert verdict == SealVerdict.FINAL_FAIL

    async def test_all_gates_pass_but_snapshot_tampered_returns_final_fail(self) -> None:
        judge, _, _, _ = _make_judge(
            gates=[{"gate_result": "PASS"}],
            hash_ok=False,
            declaration={"declaration_status": "EFFECTIVE"},
        )
        verdict = await judge.judge(uuid4())
        assert verdict == SealVerdict.FINAL_FAIL

    async def test_declaration_missing_raises(self) -> None:
        judge, _, _, _ = _make_judge(
            gates=[{"gate_result": "PASS"}],
            hash_ok=True,
            declaration=None,
        )
        with pytest.raises(RELError) as exc:
            await judge.judge(uuid4())
        assert exc.value.code == RELErrorCode.FREEZE_DECLARATION_MISSING

    async def test_declaration_not_effective_raises(self) -> None:
        judge, _, _, _ = _make_judge(
            gates=[{"gate_result": "PASS"}],
            hash_ok=True,
            declaration={"declaration_status": "DRAFT"},
        )
        with pytest.raises(RELError) as exc:
            await judge.judge(uuid4())
        assert exc.value.code == RELErrorCode.FREEZE_DECLARATION_ALREADY_EFFECTIVE

    async def test_all_pass_returns_final_pass(self) -> None:
        judge, _, _, _ = _make_judge(
            gates=[{"gate_result": "PASS"}, {"gate_result": "PASS"}],
            hash_ok=True,
            declaration={"declaration_status": "EFFECTIVE"},
        )
        verdict = await judge.judge(uuid4())
        assert verdict == SealVerdict.FINAL_PASS

    async def test_gate_fail_short_circuits_before_snapshot_check(self) -> None:
        judge, _, snapshot_repo, _ = _make_judge(
            gates=[{"gate_result": "FAIL"}],
            hash_ok=True,
            declaration={"declaration_status": "EFFECTIVE"},
        )
        await judge.judge(uuid4())
        snapshot_repo.verify_hash.assert_not_called()

    async def test_declaration_revoked_raises(self) -> None:
        judge, _, _, _ = _make_judge(
            gates=[{"gate_result": "PASS"}],
            hash_ok=True,
            declaration={"declaration_status": "REVOKED"},
        )
        with pytest.raises(RELError) as exc:
            await judge.judge(uuid4())
        assert exc.value.code == RELErrorCode.FREEZE_DECLARATION_ALREADY_EFFECTIVE