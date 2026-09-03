"""TreasuryAccountAggregate + TreasuryTransferAggregate 单元测试。

覆盖：
- available_balance = balance - frozen_amount
- freeze / unfreeze / deposit / withdraw
- 冻结超额拒绝 (TREASURY_FREEZE_EXCEED)
- 取款超额拒绝 (TREASURY_INSUFFICIENT_BALANCE)
- 调拨同账户拒绝 (TREASURY_TRANSFER_SAME_ACCOUNT)
- 6 态调拨状态机 + 非法转换拒绝 (TREASURY_TRANSFER_INVALID_TRANSITION)
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.aggregates.treasury_account_aggregate import (
    TreasuryAccountAggregate,
)
from app.domain.fin.aggregates.treasury_transfer_aggregate import (
    TreasuryTransferAggregate,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import (
    TreasuryAccountType,
    TransferStatus,
)
from app.domain.fin.value_objects.money import Money


# ==================== TreasuryAccountAggregate ====================


def _build_account() -> TreasuryAccountAggregate:
    return TreasuryAccountAggregate.create(
        account_no="BANK-001",
        account_type=TreasuryAccountType.BANK,
        currency="CNY",
        opening_balance=Money(Decimal("10000.00")),
        tenant_id=uuid4(),
    )


class TreasuryAccountAggregateTest:
    """TreasuryAccountAggregate 余额/冻结/可用余额守恒测试。"""

    def test_create_initial_balance(self) -> None:
        acc = _build_account()
        assert acc.balance.amount == Decimal("10000.00")
        assert acc.frozen_amount.amount == Decimal("0.00")

    def test_available_balance_equals_balance_minus_frozen(self) -> None:
        acc = _build_account().freeze(Money(Decimal("3000.00")))
        assert acc.available_balance().amount == Decimal("7000.00")

    def test_available_balance_no_frozen(self) -> None:
        acc = _build_account()
        assert acc.available_balance().amount == Decimal("10000.00")

    # ---- freeze ----

    def test_freeze(self) -> None:
        acc = _build_account().freeze(Money(Decimal("2000.00")))
        assert acc.frozen_amount.amount == Decimal("2000.00")

    def test_freeze_exceed_balance_rejected(self) -> None:
        acc = _build_account()
        with pytest.raises(FINError) as exc:
            acc.freeze(Money(Decimal("10001.00")))
        assert exc.value.code == FINErrorCode.TREASURY_FREEZE_EXCEED

    def test_freeze_exceed_available_after_partial_rejected(self) -> None:
        acc = _build_account().freeze(Money(Decimal("8000.00")))
        with pytest.raises(FINError) as exc:
            acc.freeze(Money(Decimal("3000.00")))
        assert exc.value.code == FINErrorCode.TREASURY_FREEZE_EXCEED

    # ---- unfreeze ----

    def test_unfreeze(self) -> None:

        acc = _build_account().freeze(Money(Decimal("3000.00"))).unfreeze(Money(Decimal("1000.00")))
        assert acc.frozen_amount.amount == Decimal("2000.00")

    def test_unfreeze_exceed_frozen_rejected(self) -> None:
        acc = _build_account().freeze(Money(Decimal("1000.00")))
        with pytest.raises(FINError) as exc:
            acc.unfreeze(Money(Decimal("2000.00")))
        assert exc.value.code == FINErrorCode.TREASURY_FREEZE_EXCEED

    # ---- deposit ----

    def test_deposit(self) -> None:
        acc = _build_account().deposit(Money(Decimal("5000.00")))
        assert acc.balance.amount == Decimal("15000.00")

    # ---- withdraw ----

    def test_within_available_balance(self) -> None:
        acc = _build_account().freeze(Money(Decimal("3000.00"))).withdraw(Money(Decimal("5000.00")))
        assert acc.balance.amount == Decimal("5000.00")

    def test_withdraw_exceed_available_rejected(self) -> None:
        acc = _build_account().freeze(Money(Decimal("8000.00")))
        with pytest.raises(FINError) as exc:
            acc.withdraw(Money(Decimal("3000.00")))
        assert exc.value.code == FINErrorCode.TREASURY_INSUFFICIENT_BALANCE

    def test_withdraw_exceed_balance_rejected(self) -> None:
        acc = _build_account()
        with pytest.raises(FINError) as exc:
            acc.withdraw(Money(Decimal("10001.00")))
        assert exc.value.code == FINErrorCode.TREASURY_INSUFFICIENT_BALANCE

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_account()
        frozen = original.freeze(Money(Decimal("1000.00")))
        assert original.frozen_amount.amount == Decimal("0.00")
        assert frozen.frozen_amount.amount == Decimal("1000.00")
        assert original is not frozen


# ==================== TreasuryTransferAggregate ====================


def _build_transfer() -> TreasuryTransferAggregate:
    return TreasuryTransferAggregate.create(
        transfer_no="TF-001",
        from_account_id=uuid4(),
        to_account_id=uuid4(),
        transfer_amount=Money(Decimal("5000.00")),
        reason="资金调拨",
        tenant_id=uuid4(),
    )


class TreasuryTransferAggregateTest:
    """TreasuryTransferAggregate 6 态状态机测试。"""

    def test_create_initial_status_is_pending_approval(self) -> None:
        t = _build_transfer()
        assert t.status == TransferStatus.PENDING_APPROVAL
        assert t.approver_ids == ()

    def test_same_account_rejected(self) -> None:
        same_id = uuid4()
        with pytest.raises(FINError) as exc:
            TreasuryTransferAggregate.create(
                transfer_no="TF-SAME",
                from_account_id=same_id,
                to_account_id=same_id,
                transfer_amount=Money(Decimal("100.00")),
                reason="x",
                tenant_id=uuid4(),
            )
        assert exc.value.code == FINErrorCode.TREASURY_TRANSFER_SAME_ACCOUNT

    # ---- 主路径 ----

    def test_pending_to_approved(self) -> None:
        t = _build_transfer().approve("approver-01")
        assert t.status == TransferStatus.APPROVED
        assert t.approver_ids == ("approver-01",)

    def test_approved_to_executing(self) -> None:
        t = _build_transfer().approve("a01").execute()
        assert t.status == TransferStatus.EXECUTING

    def test_executing_to_success(self) -> None:
        t = _build_transfer().approve("a01").execute().transfer_success()
        assert t.status == TransferStatus.SUCCESS

    def test_executing_to_failed(self) -> None:
        t = _build_transfer().approve("a01").execute().transfer_fail("余额不足")
        assert t.status == TransferStatus.FAILED

    def test_full_happy_path(self) -> None:
        t = _build_transfer().approve("a01").execute().transfer_success()
        assert t.status == TransferStatus.SUCCESS

    # ---- 取消分支 ----

    def test_pending_to_cancelled(self) -> None:
        t = _build_transfer().cancel()
        assert t.status == TransferStatus.CANCELLED

    def test_failed_to_cancelled(self) -> None:
        t = _build_transfer().approve("a01").execute().transfer_fail("x").cancel()
        assert t.status == TransferStatus.CANCELLED

    # ---- 非法转换拒绝 ----

    def test_approve_from_approved_rejected(self) -> None:
        t = _build_transfer().approve("a01")
        with pytest.raises(FINError) as exc:
            t.approve("a02")
        assert exc.value.code == FINErrorCode.TREASURY_TRANSFER_INVALID_TRANSITION

    def test_execute_from_pending_rejected(self) -> None:
        t = _build_transfer()
        with pytest.raises(FINError) as exc:
            t.execute()
        assert exc.value.code == FINErrorCode.TREASURY_TRANSFER_INVALID_TRANSITION

    def test_transfer_success_from_approved_rejected(self) -> None:
        t = _build_transfer().approve("a01")
        with pytest.raises(FINError) as exc:
            t.transfer_success()
        assert exc.value.code == FINErrorCode.TREASURY_TRANSFER_INVALID_TRANSITION

    def test_cancel_from_executing_rejected(self) -> None:
        t = _build_transfer().approve("a01").execute()
        with pytest.raises(FINError) as exc:
            t.cancel()
        assert exc.value.code == FINErrorCode.TREASURY_TRANSFER_INVALID_TRANSITION

    def test_cancel_from_success_rejected(self) -> None:
        t = _build_transfer().approve("a01").execute().transfer_success()
        with pytest.raises(FINError) as exc:
            t.cancel()
        assert exc.value.code == FINErrorCode.TREASURY_TRANSFER_INVALID_TRANSITION

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_transfer()
        approved = original.approve("a01")
        assert original.status == TransferStatus.PENDING_APPROVAL
        assert approved.status == TransferStatus.APPROVED
        assert original is not approved