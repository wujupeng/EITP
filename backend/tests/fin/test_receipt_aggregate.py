"""ReceiptAggregate 单元测试 - 4 态状态机 + 核销金额守恒。

覆盖：
- PENDING_CONFIRM→CONFIRMED→WRITE_OFF 主路径
- PENDING_CONFIRM/CONFIRMED→CANCELLED 取消分支
- 核销超额拒绝 (RECEIPT_WRITEOFF_EXCEED)
- 非法转换拒绝 (RECEIPT_INVALID_TRANSITION)
- remaining_amount 剩余金额计算
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.aggregates.receipt_aggregate import (
    ReceiptAggregate,
    WriteOffLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import ReceiptStatus
from app.domain.fin.value_objects.money import Money


def _build_receipt() -> ReceiptAggregate:
    return ReceiptAggregate.create(
        receipt_no="RCV-001",
        receipt_amount=Money(Decimal("1000.00")),
        receiver_account="ACC-001",
        payer_account="ACC-002",
        tenant_id=uuid4(),
        bank_ref="BANK-REF-001",
    )


class ReceiptAggregateTest:
    """ReceiptAggregate 4 态状态机与核销守恒测试。"""

    def test_create_initial_status_is_pending_confirm(self) -> None:
        r = _build_receipt()
        assert r.status == ReceiptStatus.PENDING_CONFIRM
        assert r.write_off_lines == ()

    # ---- 主路径 ----

    def test_pending_to_confirmed(self) -> None:
        r = _build_receipt().confirm()
        assert r.status == ReceiptStatus.CONFIRMED

    def test_confirmed_to_write_off(self) -> None:
        r = _build_receipt().confirm().write_off(
            [WriteOffLine(line_no=1, ar_voucher_no="AR-001", write_off_amount=Money(Decimal("1000.00")))]
        )
        assert r.status == ReceiptStatus.WRITE_OFF
        assert len(r.write_off_lines) == 1

    def test_partial_write_off(self) -> None:
        r = _build_receipt().confirm().write_off(
            [WriteOffLine(line_no=1, ar_voucher_no="AR-001", write_off_amount=Money(Decimal("400.00")))]
        )
        assert r.status == ReceiptStatus.WRITE_OFF
        assert r.remaining_amount().amount == Decimal("600.00")

    # ---- 取消分支 ----

    def test_pending_to_cancelled(self) -> None:
        r = _build_receipt().cancel()
        assert r.status == ReceiptStatus.CANCELLED

    def test_confirmed_to_cancelled(self) -> None:
        r = _build_receipt().confirm().cancel()
        assert r.status == ReceiptStatus.CANCELLED

    # ---- 核销超额拒绝 ----

    def test_write_off_exceed_rejected(self) -> None:
        r = _build_receipt().confirm()
        with pytest.raises(FINError) as exc:
            r.write_off(
                [WriteOffLine(line_no=1, ar_voucher_no="AR-001", write_off_amount=Money(Decimal("1001.00")))]
            )
        assert exc.value.code == FINErrorCode.RECEIPT_WRITEOFF_EXCEED

    def test_write_off_multi_lines_exceed_rejected(self) -> None:
        r = _build_receipt().confirm()
        with pytest.raises(FINError) as exc:
            r.write_off(
                [
                    WriteOffLine(line_no=1, ar_voucher_no="AR-001", write_off_amount=Money(Decimal("600.00"))),
                    WriteOffLine(line_no=2, ar_voucher_no="AR-002", write_off_amount=Money(Decimal("500.00"))),
                ]
            )
        assert exc.value.code == FINErrorCode.RECEIPT_WRITEOFF_EXCEED

    # ---- 非法转换拒绝 ----

    def test_confirm_from_confirmed_rejected(self) -> None:
        r = _build_receipt().confirm()
        with pytest.raises(FINError) as exc:
            r.confirm()
        assert exc.value.code == FINErrorCode.RECEIPT_INVALID_TRANSITION

    def test_write_off_from_pending_rejected(self) -> None:
        r = _build_receipt()
        with pytest.raises(FINError) as exc:
            r.write_off(
                [WriteOffLine(line_no=1, ar_voucher_no="AR-001", write_off_amount=Money(Decimal("100.00")))]
            )
        assert exc.value.code == FINErrorCode.RECEIPT_INVALID_TRANSITION

    def test_cancel_from_write_off_rejected(self) -> None:
        r = _build_receipt().confirm().write_off(
            [WriteOffLine(line_no=1, ar_voucher_no="AR-001", write_off_amount=Money(Decimal("1000.00")))]
        )
        with pytest.raises(FINError) as exc:
            r.cancel()
        assert exc.value.code == FINErrorCode.RECEIPT_INVALID_TRANSITION

    # ---- 剩余金额 ----

    def test_remaining_amount_no_write_off(self) -> None:
        r = _build_receipt()
        assert r.remaining_amount().amount == Decimal("1000.00")

    def test_remaining_amount_after_partial_write_off(self) -> None:
        r = _build_receipt().confirm().write_off(
            [WriteOffLine(line_no=1, ar_voucher_no="AR-001", write_off_amount=Money(Decimal("300.00")))]
        )
        assert r.remaining_amount().amount == Decimal("700.00")

    def test_remaining_amount_after_multi_line_write_off(self) -> None:
        r = (
            _build_receipt()
            .confirm()
            .write_off(
                [
                    WriteOffLine(line_no=1, ar_voucher_no="AR-001", write_off_amount=Money(Decimal("300.00"))),
                    WriteOffLine(line_no=2, ar_voucher_no="AR-002", write_off_amount=Money(Decimal("200.00"))),
                ]
            )
        )
        # 覆盖 _total_write_off 多行累加分支
        assert r.remaining_amount().amount == Decimal("500.00")

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_receipt()
        confirmed = original.confirm()
        assert original.status == ReceiptStatus.PENDING_CONFIRM
        assert confirmed.status == ReceiptStatus.CONFIRMED
        assert original is not confirmed