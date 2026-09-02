"""PROD ProductionReadinessDossierAggregate + NineQuestionsAnswerer 单元测试。

覆盖证明书状态流转 DRAFT→PENDING_SIGN→SIGNED/INVALID、assemble 填充、
sign/invalidate 副作用、非法转换抛 PRODError、frozen 不可变性，
以及 NineQuestionsAnswerer 将 16 项验证结论映射至 9 个关键问题（能/不能/待定）。
"""

from __future__ import annotations

import os
import sys
from dataclasses import FrozenInstanceError, is_dataclass
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.application.prod.dossier.nine_questions_answerer import NineQuestionsAnswerer
from app.domain.prod.dossier.aggregates.production_readiness_dossier_aggregate import (
    ProductionReadinessDossierAggregate,
)
from app.domain.prod.engine.enums import (
    DossierStatus,
    DossierVerdict,
    VerificationConclusion,
    VerificationItem,
)
from app.domain.prod.error_codes import PRODErrorCode
from app.domain.prod.exceptions import PRODError


def _make_dossier() -> ProductionReadinessDossierAggregate:
    return ProductionReadinessDossierAggregate.create(tenant_scope=uuid4())


class ProductionReadinessDossierAggregateTest:
    """生产就绪证明书聚合根状态流转与不可变性测试。"""

    # --- create() ---

    def test_create_initial_state_is_draft(self) -> None:
        d = _make_dossier()
        assert d.status == DossierStatus.DRAFT
        assert d.version == 1
        assert d.verdict is None
        assert d.signer is None
        assert d.signed_at is None
        assert d.valid_until is None
        assert d.verification_run_ids == []
        assert d.nine_questions_answers == {}
        assert d.evidence_aggregate_hash == ""

    def test_create_generates_dossier_number_when_empty(self) -> None:
        d = _make_dossier()
        assert d.dossier_number.startswith("DOSSIER-")
        assert len(d.dossier_number) > len("DOSSIER-")

    def test_create_uses_provided_dossier_number(self) -> None:
        d = ProductionReadinessDossierAggregate.create(tenant_scope=uuid4(), dossier_number="CUSTOM-001")
        assert d.dossier_number == "CUSTOM-001"

    # --- assemble ---

    def test_assemble_sets_run_ids_answers_and_evidence_hash(self) -> None:
        run_ids = [uuid4(), uuid4()]
        answers = {"Q1": "能"}
        d = _make_dossier().assemble(
            run_ids=run_ids,
            nine_questions_answers=answers,
            evidence_aggregate_hash="a" * 64,
        )
        assert d.verification_run_ids == run_ids
        assert d.nine_questions_answers == answers
        assert d.evidence_aggregate_hash == "a" * 64
        # assemble 不改变状态
        assert d.status == DossierStatus.DRAFT

    # --- 合法转换 ---

    def test_submit_for_signing_transitions_draft_to_pending_sign(self) -> None:
        d = _make_dossier().submit_for_signing()
        assert d.status == DossierStatus.PENDING_SIGN

    def test_sign_transitions_pending_sign_to_signed(self) -> None:
        from datetime import datetime, timedelta, timezone

        valid_until = datetime.now(timezone.utc) + timedelta(days=365)
        d = _make_dossier().submit_for_signing().sign(signer="admin-001", valid_until=valid_until)
        assert d.status == DossierStatus.SIGNED

    def test_sign_sets_signer_valid_until_and_verdict_ready(self) -> None:
        from datetime import datetime, timedelta, timezone

        valid_until = datetime.now(timezone.utc) + timedelta(days=365)
        d = _make_dossier().submit_for_signing().sign(signer="admin-001", valid_until=valid_until)
        assert d.signer == "admin-001"
        assert d.valid_until == valid_until
        assert d.signed_at is not None
        assert d.verdict == DossierVerdict.READY

    def test_invalidate_from_draft_sets_verdict_not_ready(self) -> None:
        d = _make_dossier().invalidate("证据缺失")
        assert d.status == DossierStatus.INVALID
        assert d.verdict == DossierVerdict.NOT_READY

    def test_invalidate_from_pending_sign(self) -> None:
        d = _make_dossier().submit_for_signing().invalidate("撤回")
        assert d.status == DossierStatus.INVALID

    def test_invalidate_from_signed(self) -> None:
        from datetime import datetime, timedelta, timezone

        valid_until = datetime.now(timezone.utc) + timedelta(days=365)
        d = _make_dossier().submit_for_signing().sign(signer="a", valid_until=valid_until).invalidate("过期失效")
        assert d.status == DossierStatus.INVALID

    # --- 非法转换 ---

    def test_illegal_submit_for_signing_from_signed_raises(self) -> None:
        from datetime import datetime, timedelta, timezone

        valid_until = datetime.now(timezone.utc) + timedelta(days=365)
        d = _make_dossier().submit_for_signing().sign(signer="a", valid_until=valid_until)
        with pytest.raises(PRODError) as exc:
            d.submit_for_signing()
        assert exc.value.code == PRODErrorCode.DOSSIER_PREREQUISITE_NOT_MET

    def test_illegal_sign_from_draft_raises(self) -> None:
        from datetime import datetime, timedelta, timezone

        valid_until = datetime.now(timezone.utc) + timedelta(days=365)
        with pytest.raises(PRODError):
            _make_dossier().sign(signer="a", valid_until=valid_until)

    def test_illegal_invalidate_from_invalid_terminal_raises(self) -> None:
        d = _make_dossier().invalidate("已失效")
        with pytest.raises(PRODError):
            d.invalidate("再次失效")

    # --- 不可变性 ---

    def test_frozen_dossier_is_immutable(self) -> None:
        d = _make_dossier()
        assert is_dataclass(d)
        with pytest.raises(FrozenInstanceError):
            d.status = DossierStatus.SIGNED  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            d.signer = "tampered"  # type: ignore[misc]


class NineQuestionsAnswererTest:
    """NineQuestionsAnswerer 16 项验证结论 → 9 个关键问题映射测试。"""

    def test_answer_all_pass_returns_neng_for_every_question(self) -> None:
        results = {item: VerificationConclusion.PASS for item in VerificationItem}
        answers = NineQuestionsAnswerer().answer(results)
        # 恰好 9 个问题
        assert len(answers) == 9
        # 全 PASS 时每个问题结论为"能"
        for q, ans in answers.items():
            assert ans["conclusion"] == "能", f"{q} 应为能"
            assert "evidence" in ans and "details" in ans

    def test_answer_with_fail_and_inconclusive_propagates(self) -> None:
        # Q1_capacity 依赖 BASELINE+CONCURRENT；让 BASELINE FAIL → Q1 不能
        # Q4_upgrade 仅依赖 REGRESSION；让 REGRESSION INCONCLUSIVE → Q4 待定
        results = {item: VerificationConclusion.PASS for item in VerificationItem}
        results[VerificationItem.BASELINE] = VerificationConclusion.FAIL
        results[VerificationItem.REGRESSION] = VerificationConclusion.INCONCLUSIVE
        answers = NineQuestionsAnswerer().answer(results)
        assert answers["Q1_capacity"]["conclusion"] == "不能"
        assert answers["Q4_upgrade"]["conclusion"] == "待定"
        # 未受影响的 Q5_backup 仍为"能"
        assert answers["Q5_backup"]["conclusion"] == "能"
        # Q7_audit 映射为空列表，恒为"能"且 evidence 指向 PLT 审计中心
        assert answers["Q7_audit"]["conclusion"] == "能"
        assert "PLT-001" in answers["Q7_audit"]["evidence"][0]