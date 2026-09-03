"""PaymentAggregate 单元测试 - 7 态状态机 + 非法转换拒绝。

覆盖：
- DRAFT→PENDING_APPROVAL→APPROVED→EXECUTING→SUCCESS 主路径
- EXECUTING→FAILED 失败分支
- PENDING_APPROVAL→DRAFT 驳回分支
- DRAFT/PENDING_APPROVAL/FAILED→CANCELLED 取消分支
- 非法转换拒绝 (PAYMENT_INVALID_TRANSITION / PAYMENT_CANCEL_FORBIDDEN)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.aggregates.payment_aggregate import PaymentAggregate
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import PaymentMethod, PaymentStatus
from app.domain.fin.value_objects.money import Money


def _build_payment() -> PaymentAggregate:
    return PaymentAggregate.create(
        payment_no="PAY-001",
        ap_voucher_no="AP-001",
        payment_amount=Money(Decimal("1000.00")),
        payment_method=PaymentMethod.BANK_TRANSFER,
        payment_account="ACC-001",
        payee_account="ACC-002",
        tenant_id=uuid4(),
        expected_payment_date=date(2026, 9, 30),
    )


class PaymentAggregateTest:
    """PaymentAggregate 7 态状态机测试。"""

    def test_create_initial_status_is_draft(self) -> None:
        p = _build_payment()
        assert p.status == PaymentStatus.DRAFT
        assert p.approver_id is None
        assert p.bank_ref is None

    # ---- 主路径 ----

    def test_draft_to_pending_approval(self) -> None:
        p = _build_payment().submit()
        assert p.status == PaymentStatus.PENDING_APPROVAL

    def test_pending_to_approved(self) -> None:
        p = _build_payment().submit().approve("approver-01", "同意")
        assert p.status == PaymentStatus.APPROVED
        assert p.approver_id == "approver-01"
        assert p.approval_opinion == "同意"

    def test_approved_to_executing(self) -> None:
        p = _build_payment().submit().approve("a01").execute()
        assert p.status == PaymentStatus.EXECUTING

    def test_executing_to_success(self) -> None:
        p = (
            _build_payment()
            .submit()
            .approve("a01")
            .execute()
            .bank_callback_success("BANK-REF-001")
        )
        assert p.status == PaymentStatus.SUCCESS
        assert p.bank_ref == "BANK-REF-001"
        assert p.actual_payment_date == date.today()

    def test_full_happy_path(self) -> None:
        p = (
            _build_payment()
            .submit()
            .approve("a01")
            .execute()
            .bank_callback_success("BANK-REF-001", date(2026, 9, 15))
        )
        assert p.status == PaymentStatus.SUCCESS
        assert p.actual_payment_date == date(2026, 9, 15)

    # ---- 失败分支 ----

    def test_executing_to_failed(self) -> None:
        p = (
            _build_payment()
            .submit()
            .approve("a01")
            .execute()
            .bank_callback_failed("余额不足")
        )
        assert p.status == PaymentStatus.FAILED
        assert p.approval_opinion == "余额不足"

    # ---- 驳回分支 ----

    def test_pending_to_draft_reject(self) -> None:
        p = _build_payment().submit().reject("a01", "信息有误")
        assert p.status == PaymentStatus.DRAFT
        assert p.approver_id == "a01"

    # ---- 取消分支 ----

    def test_draft_to_cancelled(self) -> None:
        p = _build_payment().cancel()
        assert p.status == PaymentStatus.CANCELLED

    def test_pending_to_cancelled(self) -> None:
        p = _build_payment().submit().cancel()
        assert p.status == PaymentStatus.CANCELLED

    def test_failed_to_cancelled(self) -> None:
        p = (
            _build_payment()
            .submit()
            .approve("a01")
            .execute()
            .bank_callback_failed("x")
            .cancel()
        )
        assert p.status == PaymentStatus.CANCELLED

    # ---- 非法转换拒绝 ----

    def test_submit_from_pending_rejected(self) -> None:
        p = _build_payment().submit()
        with pytest.raises(FINError) as exc:
            p.submit()
        assert exc.value.code == FINErrorCode.PAYMENT_INVALID_TRANSITION

    def test_approve_from_draft_rejected(self) -> None:
        p = _build_payment()
        with pytest.raises(FINError) as exc:
            p.approve("a01")
        assert exc.value.code == FINErrorCode.PAYMENT_INVALID_TRANSITION

    def test_execute_from_pending_rejected(self) -> None:
        p = _build_payment().submit()
        with pytest.raises(FINError) as exc:
            p.execute()
        assert exc.value.code == FINErrorCode.PAYMENT_INVALID_TRANSITION

    def test_success_from_approved_rejected(self) -> None:
        p = _build_payment().submit().approve("a01")
        with pytest.raises(FINError) as exc:
            p.bank_callback_success("ref")
        assert exc.value.code == FINErrorCode.PAYMENT_INVALID_TRANSITION

    def test_cancel_from_success_rejected(self) -> None:
        p = (
            _build_payment()
            .submit()
            .approve("a01")
            .execute()
            .bank_callback_success("ref")
        )
        with pytest.raises(FINError) as exc:
            p.cancel()
        assert exc.value.code == FINErrorCode.PAYMENT_CANCEL_FORBIDDEN

    def test_cancel_from_executing_rejected(self) -> None:
        p = _build_payment().submit().approve("a01").execute()
        with pytest.raises(FINError) as exc:
            p.cancel()
        assert exc.value.code == FINErrorCode.PAYMENT_CANCEL_FORBIDDEN

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_payment()
        submitted = original.submit()
        assert original.status == PaymentStatus.DRAFT
        assert submitted.status == PaymentStatus.PENDING_APPROVAL
        assert original is not submitted