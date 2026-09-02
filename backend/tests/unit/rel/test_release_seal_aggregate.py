"""ReleaseSealAggregate 单元测试 - 9 状态机转换 / 终态保护 / co_sign 校验 / 不可变性。

状态机: REQUESTED → GATE_RUNNING → SNAPSHOT_COLLECTING → REPORT_ASSEMBLING
        → PENDING_CO_SIGN → SEALED (happy path)
        各阶段可分流至 GATE_FAILED / SNAPSHOT_FAILED / FAILED 终态。
覆盖 request_seal 初始态、合法转换、非法转换抛 RELError、终态保护、
co_sign 仅在 PENDING_CO_SIGN 可用、setter 副作用、frozen dataclass 不可变性。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from uuid import UUID

import pytest

from app.domain.rel.aggregates.release_seal_aggregate import ReleaseSealAggregate
from app.domain.rel.enums import SealStatus, SealVerdict
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


def _make_seal() -> ReleaseSealAggregate:
    """构造一个处于 REQUESTED 初始态的封版聚合根。"""
    return ReleaseSealAggregate.request_seal(
        release_number="EITP-REL-001",
        version="1.0.0",
        git_tag="v1.0.0",
    )


class ReleaseSealAggregateTest:
    """ReleaseSealAggregate 9 状态机与不可变性测试。"""

    # --- request_seal() 初始态 ---

    def test_request_seal_initial_state_is_requested(self) -> None:
        seal = _make_seal()
        assert seal.seal_status == SealStatus.REQUESTED
        assert seal.verdict is None
        assert seal.seal_time is None
        assert seal.signed_by_releaser is None
        assert seal.signed_by_security is None
        assert seal.signed_at is None
        assert seal.git_commit_sha is None
        assert seal.core_freeze_baseline_hash is None
        assert seal.evidence_hash is None

    def test_request_seal_assigns_release_id_and_metadata(self) -> None:
        seal = _make_seal()
        assert isinstance(seal.release_id, UUID)
        assert seal.release_number == "EITP-REL-001"
        assert seal.version == "1.0.0"
        assert seal.git_tag == "v1.0.0"

    def test_request_seal_generates_unique_release_ids(self) -> None:
        seal_a = _make_seal()
        seal_b = _make_seal()
        assert seal_a.release_id != seal_b.release_id

    # --- 合法正向转换 ---

    def test_start_gate_transitions_to_gate_running(self) -> None:
        seal = _make_seal().start_gate()
        assert seal.seal_status == SealStatus.GATE_RUNNING

    def test_start_snapshot_from_gate_running(self) -> None:
        seal = _make_seal().start_gate().start_snapshot()
        assert seal.seal_status == SealStatus.SNAPSHOT_COLLECTING

    def test_start_report_assembly_from_snapshot_collecting(self) -> None:
        seal = _make_seal().start_gate().start_snapshot().start_report_assembly()
        assert seal.seal_status == SealStatus.REPORT_ASSEMBLING

    def test_pending_co_sign_from_report_assembling(self) -> None:
        seal = _make_seal().start_gate().start_snapshot().start_report_assembly().pending_co_sign()
        assert seal.seal_status == SealStatus.PENDING_CO_SIGN

    def test_co_sign_transitions_to_sealed_with_final_pass(self) -> None:
        seal = (
            _make_seal()
            .start_gate()
            .start_snapshot()
            .start_report_assembly()
            .pending_co_sign()
            .co_sign(releaser="alice", security_officer="bob")
        )
        assert seal.seal_status == SealStatus.SEALED
        assert seal.verdict == SealVerdict.FINAL_PASS
        assert seal.signed_by_releaser == "alice"
        assert seal.signed_by_security == "bob"
        assert seal.signed_at is not None
        assert seal.seal_time is not None

    # --- 合法失败分流转换 ---

    def test_mark_gate_failed_from_gate_running(self) -> None:
        seal = _make_seal().start_gate().mark_gate_failed()
        assert seal.seal_status == SealStatus.GATE_FAILED

    def test_mark_snapshot_failed_from_snapshot_collecting(self) -> None:
        seal = _make_seal().start_gate().start_snapshot().mark_snapshot_failed()
        assert seal.seal_status == SealStatus.SNAPSHOT_FAILED

    def test_mark_failed_from_requested(self) -> None:
        seal = _make_seal().mark_failed()
        assert seal.seal_status == SealStatus.FAILED

    def test_mark_failed_from_report_assembling(self) -> None:
        seal = _make_seal().start_gate().start_snapshot().start_report_assembly().mark_failed()
        assert seal.seal_status == SealStatus.FAILED

    def test_mark_failed_from_pending_co_sign(self) -> None:
        seal = (
            _make_seal()
            .start_gate()
            .start_snapshot()
            .start_report_assembly()
            .pending_co_sign()
            .mark_failed()
        )
        assert seal.seal_status == SealStatus.FAILED

    # --- 非法转换 ---

    def test_start_gate_from_gate_running_raises(self) -> None:
        with pytest.raises(RELError) as exc:
            _make_seal().start_gate().start_gate()
        assert exc.value.code == RELErrorCode.SEAL_INVALID_STATE_TRANSITION

    def test_start_snapshot_from_requested_raises(self) -> None:
        with pytest.raises(RELError):
            _make_seal().start_snapshot()

    def test_co_sign_from_requested_raises(self) -> None:
        with pytest.raises(RELError) as exc:
            _make_seal().co_sign("alice", "bob")
        assert exc.value.code == RELErrorCode.SEAL_INVALID_STATE_TRANSITION

    def test_co_sign_from_sealed_raises(self) -> None:
        sealed = (
            _make_seal()
            .start_gate()
            .start_snapshot()
            .start_report_assembly()
            .pending_co_sign()
            .co_sign("alice", "bob")
        )
        with pytest.raises(RELError):
            sealed.co_sign("alice", "bob")

    def test_pending_co_sign_from_requested_raises(self) -> None:
        with pytest.raises(RELError):
            _make_seal().pending_co_sign()

    # --- 终态保护 ---

    def test_sealed_terminal_cannot_transition(self) -> None:
        sealed = (
            _make_seal()
            .start_gate()
            .start_snapshot()
            .start_report_assembly()
            .pending_co_sign()
            .co_sign("alice", "bob")
        )
        with pytest.raises(RELError) as exc:
            sealed.start_gate()
        assert exc.value.code == RELErrorCode.SEAL_INVALID_STATE_TRANSITION
        assert "terminal" in exc.value.message

    def test_gate_failed_terminal_cannot_transition(self) -> None:
        failed = _make_seal().start_gate().mark_gate_failed()
        with pytest.raises(RELError):
            failed.start_snapshot()

    def test_snapshot_failed_terminal_cannot_transition(self) -> None:
        failed = _make_seal().start_gate().start_snapshot().mark_snapshot_failed()
        with pytest.raises(RELError):
            failed.start_report_assembly()

    def test_failed_terminal_cannot_transition(self) -> None:
        failed = _make_seal().mark_failed()
        with pytest.raises(RELError):
            failed.start_gate()

    # --- co_sign 校验 ---

    def test_co_sign_records_both_signers(self) -> None:
        seal = (
            _make_seal()
            .start_gate()
            .start_snapshot()
            .start_report_assembly()
            .pending_co_sign()
            .co_sign(releaser="releaser_a", security_officer="security_b")
        )
        assert seal.signed_by_releaser == "releaser_a"
        assert seal.signed_by_security == "security_b"
        assert seal.signed_at == seal.seal_time

    def test_co_sign_only_allowed_in_pending_co_sign(self) -> None:
        seal = _make_seal().start_gate().start_snapshot().start_report_assembly()
        with pytest.raises(RELError) as exc:
            seal.co_sign("a", "b")
        assert "PENDING_CO_SIGN" in exc.value.message

    # --- setter 副作用 ---

    def test_set_git_commit_sha(self) -> None:
        seal = _make_seal().set_git_commit_sha("abc123")
        assert seal.git_commit_sha == "abc123"

    def test_set_core_freeze_hash(self) -> None:
        seal = _make_seal().set_core_freeze_hash("deadbeef")
        assert seal.core_freeze_baseline_hash == "deadbeef"

    def test_set_test_counts(self) -> None:
        seal = _make_seal().set_test_counts(total=378, passed=378)
        assert seal.test_total_count == 378
        assert seal.test_passed_count == 378

    def test_set_evidence_hash(self) -> None:
        seal = _make_seal().set_evidence_hash("a" * 64)
        assert seal.evidence_hash == "a" * 64

    def test_setters_preserve_seal_status(self) -> None:
        seal = _make_seal().set_git_commit_sha("sha")
        assert seal.seal_status == SealStatus.REQUESTED

    # --- 不可变性 ---

    def test_frozen_dataclass_is_immutable(self) -> None:
        seal = _make_seal()
        assert is_dataclass(seal)
        with pytest.raises(FrozenInstanceError):
            seal.seal_status = SealStatus.SEALED  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            seal.verdict = SealVerdict.FINAL_PASS  # type: ignore[misc]

    def test_transition_returns_new_instance_not_mutating_original(self) -> None:
        seal = _make_seal()
        next_seal = seal.start_gate()
        assert seal.seal_status == SealStatus.REQUESTED
        assert next_seal.seal_status == SealStatus.GATE_RUNNING
        assert seal is not next_seal

    # --- 完整成功路径 ---

    def test_full_happy_path_requested_to_sealed(self) -> None:
        seal = (
            _make_seal()
            .start_gate()
            .start_snapshot()
            .start_report_assembly()
            .pending_co_sign()
            .co_sign(releaser="alice", security_officer="bob")
        )
        assert seal.seal_status == SealStatus.SEALED
        assert seal.verdict == SealVerdict.FINAL_PASS
        assert seal.signed_by_releaser == "alice"
        assert seal.signed_by_security == "bob"
        assert seal.seal_time is not None
        assert seal.signed_at is not None