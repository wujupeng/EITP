"""PROD VerificationRunAggregate 单元测试 - 状态机驱动 + append-only 不可篡改。

状态机: PENDING → RUNNING → EVIDENCE_COLLECTING → COMPLETED/FAILED/INCONCLUSIVE
覆盖 create() 初始态、合法转换、非法转换抛 PRODError、complete/fail/mark_inconclusive
副作用字段、retry 重置、frozen dataclass 不可变性、完整成功路径。
"""

from __future__ import annotations

import os
import sys
from dataclasses import FrozenInstanceError, is_dataclass
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.domain.prod.engine.aggregates.verification_run_aggregate import VerificationRunAggregate
from app.domain.prod.engine.enums import (
    ExecutorRole,
    VerificationConclusion,
    VerificationEnvironment,
    VerificationItem,
    VerificationStatus,
)
from app.domain.prod.error_codes import PRODErrorCode
from app.domain.prod.exceptions import PRODError


def _make_run() -> VerificationRunAggregate:
    """构造一个处于 PENDING 初始态的验证执行聚合根。"""
    return VerificationRunAggregate.create(
        tenant_id=uuid4(),
        verification_item=VerificationItem.BASELINE,
        executor=ExecutorRole.SRE,
        environment=VerificationEnvironment.STAGING,
        config_snapshot={"threshold": 0.99},
        trace_id="trace-001",
    )


class VerificationRunAggregateTest:
    """VerificationRunAggregate 状态机与不可变性测试。"""

    # --- create() 初始态 ---

    def test_create_initial_state_is_pending(self) -> None:
        run = _make_run()
        assert run.status == VerificationStatus.PENDING
        assert run.conclusion is None

    def test_create_initial_temporal_and_evidence_fields_are_none(self) -> None:
        run = _make_run()
        assert run.started_at is None
        assert run.finished_at is None
        assert run.evidence_hash is None
        assert run.evidence_report_path is None
        assert run.evidence_metrics_snapshot_path is None
        assert run.evidence_log_path is None
        assert run.failure_detail is None
        assert run.config_snapshot == {"threshold": 0.99}

    # --- 合法转换 ---

    def test_start_transitions_pending_to_running_and_sets_started_at(self) -> None:
        run = _make_run().start()
        assert run.status == VerificationStatus.RUNNING
        assert run.started_at is not None

    def test_enter_evidence_collecting_from_running(self) -> None:
        run = _make_run().start().enter_evidence_collecting()
        assert run.status == VerificationStatus.EVIDENCE_COLLECTING

    def test_complete_from_evidence_collecting_sets_pass_and_evidence(self) -> None:
        run = _make_run().start().enter_evidence_collecting().complete(
            evidence_hash="a" * 64,
            evidence_report_path="/rpt.json",
            evidence_metrics_snapshot_path="/metrics.json",
            evidence_log_path="/log.txt",
        )
        assert run.status == VerificationStatus.COMPLETED
        assert run.conclusion == VerificationConclusion.PASS
        assert run.finished_at is not None
        assert run.evidence_hash == "a" * 64
        assert run.evidence_report_path == "/rpt.json"

    def test_fail_from_pending_sets_fail_conclusion_and_detail(self) -> None:
        run = _make_run().fail("EITP_PROD_BASELINE_LOW_CONFIDENCE", {"p": 0.8})
        assert run.status == VerificationStatus.FAILED
        assert run.conclusion == VerificationConclusion.FAIL
        assert run.finished_at is not None
        assert run.failure_detail == {"error_code": "EITP_PROD_BASELINE_LOW_CONFIDENCE", "detail": {"p": 0.8}}

    def test_fail_from_running(self) -> None:
        run = _make_run().start().fail("EITP_PROD_CONCURRENT_DATA_INCONSISTENT", {})
        assert run.status == VerificationStatus.FAILED
        assert run.conclusion == VerificationConclusion.FAIL

    def test_fail_from_evidence_collecting(self) -> None:
        run = _make_run().start().enter_evidence_collecting().fail("EITP_PROD_EVIDENCE_HASH_MISMATCH", {})
        assert run.status == VerificationStatus.FAILED

    def test_mark_inconclusive_from_running_sets_reason(self) -> None:
        run = _make_run().start().mark_inconclusive("环境不稳定")
        assert run.status == VerificationStatus.INCONCLUSIVE
        assert run.conclusion == VerificationConclusion.INCONCLUSIVE
        assert run.failure_detail == {"reason": "环境不稳定"}

    def test_retry_from_failed_resets_to_pending(self) -> None:
        run = _make_run().start().fail("EITP_PROD_INTERNAL_ERROR", {})
        retried = run.retry()
        assert retried.status == VerificationStatus.PENDING
        assert retried.started_at is None
        assert retried.finished_at is None
        assert retried.conclusion is None
        assert retried.evidence_hash is None
        assert retried.failure_detail is None

    def test_retry_from_inconclusive_resets_to_pending(self) -> None:
        run = _make_run().start().mark_inconclusive("待定")
        assert run.retry().status == VerificationStatus.PENDING

    # --- 非法转换 ---

    def test_illegal_start_from_running_raises(self) -> None:
        run = _make_run().start()
        with pytest.raises(PRODError) as exc:
            run.start()
        assert exc.value.code == PRODErrorCode.VERIFICATION_PREREQUISITE_NOT_MET

    def test_illegal_complete_from_pending_raises(self) -> None:
        run = _make_run()
        with pytest.raises(PRODError):
            run.complete("h", "/r", "/m", "/l")

    def test_illegal_enter_evidence_collecting_from_pending_raises(self) -> None:
        run = _make_run()
        with pytest.raises(PRODError):
            run.enter_evidence_collecting()

    def test_illegal_start_from_completed_terminal_raises(self) -> None:
        run = _make_run().start().enter_evidence_collecting().complete("h", "/r", "/m", "/l")
        with pytest.raises(PRODError):
            run.start()

    def test_illegal_retry_from_completed_raises(self) -> None:
        run = _make_run().start().enter_evidence_collecting().complete("h", "/r", "/m", "/l")
        with pytest.raises(PRODError):
            run.retry()

    # --- 不可变性 ---

    def test_frozen_dataclass_is_immutable(self) -> None:
        run = _make_run()
        assert is_dataclass(run)
        with pytest.raises(FrozenInstanceError):
            run.status = VerificationStatus.RUNNING  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            run.evidence_hash = "tampered"  # type: ignore[misc]

    # --- 完整成功路径 ---

    def test_full_happy_path_pending_to_completed(self) -> None:
        run = (
            _make_run()
            .start()
            .enter_evidence_collecting()
            .complete(
                evidence_hash="b" * 64,
                evidence_report_path="/r.json",
                evidence_metrics_snapshot_path="/m.json",
                evidence_log_path="/l.txt",
            )
        )
        assert run.status == VerificationStatus.COMPLETED
        assert run.conclusion == VerificationConclusion.PASS
        assert run.started_at is not None
        assert run.finished_at is not None
        assert run.evidence_hash == "b" * 64