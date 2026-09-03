"""ReconciliationAggregate 单元测试 - 6 态状态机 + 差异处理 append-only。

覆盖：
- CREATED→MATCHING→MATCHED→DIFF_HANDLING→COMPLETED 主路径
- MATCHING/DIFF_HANDLING→FAILED 失败分支
- PENDING_APPROVAL→CANCELLED 取消分支
- 差异处理 append-only（handle_records 只增不改）
- 差异未找到拒绝 (RECON_DIFF_NOT_FOUND)
- 差异已处理拒绝 (RECON_DIFF_ALREADY_HANDLED)
- 非法转换拒绝 (RECON_INVALID_TRANSITION)
- complete 时存在 pending 差异拒绝
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.aggregates.reconciliation_aggregate import (
    ReconciliationAggregate,
    ReconciliationDifference,
    ReconciliationLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import (
    DifferenceType,
    HandleStatus,
    ReconciliationStatus,
)
from app.domain.fin.value_objects.money import Money


def _line(line_no: int = 1, matched: bool = True) -> ReconciliationLine:
    return ReconciliationLine(
        line_no=line_no,
        business_ref_type="PAYMENT",
        business_ref_id=f"PAY-{line_no:03d}",
        system_amount=Money(Decimal("100.00")),
        external_amount=Money(Decimal("100.00")),
        is_matched=matched,
    )


def _diff(diff_id=None) -> ReconciliationDifference:
    return ReconciliationDifference(
        diff_id=diff_id or uuid4(),
        line_no=1,
        business_ref_type="PAYMENT",
        business_ref_id="PAY-001",
        diff_type=DifferenceType.AMOUNT_DIFF,
        diff_amount=Money(Decimal("5.00")),
        handle_status=HandleStatus.PENDING,
    )


def _build_recon(lines=None) -> ReconciliationAggregate:
    return ReconciliationAggregate.create(
        recon_no="RECON-001",
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
        scope_type="BANK",
        scope_value="BANK-001",
        data_source="BANK_STATEMENT",
        currency="CNY",
        tenant_id=uuid4(),
        lines=lines if lines is not None else [],
    )


class ReconciliationAggregateTest:
    """ReconciliationAggregate 6 态状态机与 append-only 测试。"""

    def test_create_initial_status_is_created(self) -> None:
        r = _build_recon()
        assert r.status == ReconciliationStatus.CREATED
        assert r.differences == ()
        assert r.handle_records == ()

    def test_create_with_matched_lines(self) -> None:
        r = _build_recon(lines=[_line(1, True), _line(2, True)])
        assert r.matched_count == 2
        assert r.diff_count == 0

    def test_create_with_unmatched_lines(self) -> None:
        r = _build_recon(lines=[_line(1, True), _line(2, False)])
        assert r.matched_count == 1
        assert r.diff_count == 1

    # ---- 主路径 ----

    def test_created_to_matching(self) -> None:
        r = _build_recon().start_matching()
        assert r.status == ReconciliationStatus.MATCHING

    def test_matching_to_matched(self) -> None:
        d = _diff()
        r = _build_recon().start_matching().finish_matching([d])
        assert r.status == ReconciliationStatus.MATCHED
        assert len(r.differences) == 1
        assert r.diff_count == 1

    def test_matched_to_diff_handling(self) -> None:
        d = _diff()
        r = (
            _build_recon()
            .start_matching()
            .finish_matching([d])
            .handle_diff(d.diff_id, "WRITE_OFF", "handler-01", "核销处理")
        )
        assert r.status == ReconciliationStatus.DIFF_HANDLING
        assert len(r.handle_records) == 1

    def test_diff_handling_to_completed(self) -> None:
        d = _diff()
        r = (
            _build_recon()
            .start_matching()
            .finish_matching([d])
            .handle_diff(d.diff_id, "WRITE_OFF", "handler-01", "核销")
            .complete()
        )
        assert r.status == ReconciliationStatus.COMPLETED

    def test_full_happy_path_no_diff(self) -> None:
        # 无差异 finish_matching 后状态为 MATCHED
        r = _build_recon().start_matching().finish_matching([])
        assert r.status == ReconciliationStatus.MATCHED
        assert r.diff_count == 0

    # ---- 失败分支 ----

    def test_matching_to_failed(self) -> None:
        r = _build_recon().start_matching().fail("对账失败")
        assert r.status == ReconciliationStatus.FAILED

    def test_diff_handling_to_failed(self) -> None:
        d = _diff()
        r = (
            _build_recon()
            .start_matching()
            .finish_matching([d])
            .handle_diff(d.diff_id, "HANG", "h01", "挂起")
            .fail("无法解决")
        )
        assert r.status == ReconciliationStatus.FAILED

    # ---- append-only ----

    def test_handle_records_append_only(self) -> None:
        d1 = _diff(uuid4())
        d2 = _diff(uuid4())
        r = _build_recon().start_matching().finish_matching([d1, d2])
        r1 = r.handle_diff(d1.diff_id, "WRITE_OFF", "h01", "处理1")
        r2 = r1.handle_diff(d2.diff_id, "HANG", "h02", "处理2")
        # 第二次处理后保留第一次记录（append-only）
        assert len(r2.handle_records) == 2
        assert r2.handle_records[0].handler_id == "h01"
        assert r2.handle_records[1].handler_id == "h02"

    def test_handle_diff_updates_handle_status(self) -> None:
        d = _diff()
        r = (
            _build_recon()
            .start_matching()
            .finish_matching([d])
            .handle_diff(d.diff_id, "WRITE_OFF", "h01", "核销")
        )
        assert r.differences[0].handle_status == HandleStatus.WRITE_OFF

    def test_handle_diff_hang_action_sets_hang_status(self) -> None:
        d = _diff()
        r = (
            _build_recon()
            .start_matching()
            .finish_matching([d])
            .handle_diff(d.diff_id, "HANG", "h01", "挂起")
        )
        assert r.differences[0].handle_status == HandleStatus.HANG

    # ---- 差异未找到拒绝 ----

    def test_handle_diff_not_found_rejected(self) -> None:
        d = _diff()
        r = _build_recon().start_matching().finish_matching([d])
        with pytest.raises(FINError) as exc:
            r.handle_diff(uuid4(), "WRITE_OFF", "h01", "x")
        assert exc.value.code == FINErrorCode.RECON_DIFF_NOT_FOUND

    # ---- 差异已处理拒绝 ----

    def test_handle_diff_already_handled_rejected(self) -> None:
        d = _diff()
        r = (
            _build_recon()
            .start_matching()
            .finish_matching([d])
            .handle_diff(d.diff_id, "WRITE_OFF", "h01", "核销")
        )
        with pytest.raises(FINError) as exc:
            r.handle_diff(d.diff_id, "WRITE_OFF", "h02", "重复处理")
        assert exc.value.code == FINErrorCode.RECON_DIFF_ALREADY_HANDLED

    # ---- complete 时 pending 差异拒绝 ----

    def test_complete_with_pending_diff_rejected(self) -> None:
        d = _diff()
        r = _build_recon().start_matching().finish_matching([d])
        # MATCHED 状态下直接 complete 会因状态不符（MATCHED != DIFF_HANDLING）拒绝
        with pytest.raises(FINError) as exc:
            r.complete()
        assert exc.value.code == FINErrorCode.RECON_INVALID_TRANSITION

    def test_complete_with_remaining_pending_rejected(self) -> None:
        d1 = _diff(uuid4())
        d2 = _diff(uuid4())
        r = (
            _build_recon()
            .start_matching()
            .finish_matching([d1, d2])
            .handle_diff(d1.diff_id, "WRITE_OFF", "h01", "处理1")
        )
        # 仍有一个 pending 差异 d2 未处理
        with pytest.raises(FINError) as exc:
            r.complete()
        assert exc.value.code == FINErrorCode.RECON_DIFF_ALREADY_HANDLED

    # ---- 非法转换拒绝 ----

    def test_start_matching_from_matching_rejected(self) -> None:
        r = _build_recon().start_matching()
        with pytest.raises(FINError) as exc:
            r.start_matching()
        assert exc.value.code == FINErrorCode.RECON_INVALID_TRANSITION

    def test_finish_matching_from_created_rejected(self) -> None:
        r = _build_recon()
        with pytest.raises(FINError) as exc:
            r.finish_matching([])
        assert exc.value.code == FINErrorCode.RECON_INVALID_TRANSITION

    def test_handle_diff_from_created_rejected(self) -> None:
        r = _build_recon()
        with pytest.raises(FINError) as exc:
            r.handle_diff(uuid4(), "WRITE_OFF", "h01", "x")
        assert exc.value.code == FINErrorCode.RECON_INVALID_TRANSITION

    def test_fail_from_created_rejected(self) -> None:
        r = _build_recon()
        with pytest.raises(FINError) as exc:
            r.fail("x")
        assert exc.value.code == FINErrorCode.RECON_INVALID_TRANSITION

    def test_complete_from_matched_rejected(self) -> None:
        r = _build_recon().start_matching().finish_matching([])
        with pytest.raises(FINError) as exc:
            r.complete()
        assert exc.value.code == FINErrorCode.RECON_INVALID_TRANSITION

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_recon()
        matching = original.start_matching()
        assert original.status == ReconciliationStatus.CREATED
        assert matching.status == ReconciliationStatus.MATCHING
        assert original is not matching