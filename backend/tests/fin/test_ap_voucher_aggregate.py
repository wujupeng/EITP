"""APVoucherAggregate 单元测试 - 金额守恒 + 付款核销。

覆盖：
- 创建初始守恒 payable = paid + unpaid
- apply_payment 部分付款后守恒保持
- apply_payment 全额付款后状态 SETTLED
- 付款超额拒绝 (PAYMENT_EXCEED_AP)
- AP_UNBALANCED 拒绝
- mark_partial / mark_settled / mark_overdue / red_voucher
"""

from __future__ import annotations

from dataclasses import replace as dataclass_replace
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.aggregates.ap_voucher_aggregate import APVoucherAggregate
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import VoucherStatus
from app.domain.fin.value_objects.money import Money


def _build_ap() -> APVoucherAggregate:
    return APVoucherAggregate.create(
        voucher_no="AP-001",
        business_ref_type="SETTLEMENT",
        business_ref_id="ST-001",
        payable_amount=Money(Decimal("2000.00")),
        tenant_id=uuid4(),
        payment_terms="NET30",
    )


class APVoucherAggregateTest:
    """APVoucherAggregate 金额守恒与付款核销测试。"""

    def test_create_initial_balance_conserved(self) -> None:
        ap = _build_ap()
        assert ap.payable_amount.amount == Decimal("2000.00")
        assert ap.paid_amount.amount == Decimal("0.00")
        assert ap.unpaid_amount.amount == Decimal("2000.00")
        assert ap.status == VoucherStatus.OPEN
        assert Money.is_ap_conserved(ap.payable_amount, ap.paid_amount, ap.unpaid_amount)

    # ---- apply_payment ----

    def test_partial_payment_keeps_conservation(self) -> None:
        ap = _build_ap().apply_payment(Money(Decimal("500.00")))
        assert ap.paid_amount.amount == Decimal("500.00")
        assert ap.unpaid_amount.amount == Decimal("1500.00")
        assert ap.status == VoucherStatus.PARTIAL
        assert Money.is_ap_conserved(ap.payable_amount, ap.paid_amount, ap.unpaid_amount)

    def test_full_payment_settles(self) -> None:
        ap = _build_ap().apply_payment(Money(Decimal("2000.00")))
        assert ap.paid_amount.amount == Decimal("2000.00")
        assert ap.unpaid_amount.amount == Decimal("0.00")
        assert ap.status == VoucherStatus.SETTLED

    def test_multi_partial_payments(self) -> None:
        ap = _build_ap().apply_payment(Money(Decimal("500.00"))).apply_payment(Money(Decimal("1000.00")))
        assert ap.paid_amount.amount == Decimal("1500.00")
        assert ap.unpaid_amount.amount == Decimal("500.00")
        assert ap.status == VoucherStatus.PARTIAL

    # ---- 付款超额拒绝 ----

    def test_payment_exceed_unpaid_rejected(self) -> None:
        ap = _build_ap()
        with pytest.raises(FINError) as exc:
            ap.apply_payment(Money(Decimal("2001.00")))
        assert exc.value.code == FINErrorCode.PAYMENT_EXCEED_AP

    def test_payment_exceed_after_partial_rejected(self) -> None:
        ap = _build_ap().apply_payment(Money(Decimal("1800.00")))
        with pytest.raises(FINError) as exc:
            ap.apply_payment(Money(Decimal("300.00")))
        assert exc.value.code == FINErrorCode.PAYMENT_EXCEED_AP

    # ---- AP_UNBALANCED 拒绝 ----

    def test_unbalanced_construction_raises_on_check(self) -> None:
        base = _build_ap()
        unbalanced = dataclass_replace(
            base,
            paid_amount=Money(Decimal("100.00")),
            unpaid_amount=Money(Decimal("1500.00")),  # 100+1500 != 2000
        )
        with pytest.raises(FINError) as exc:
            unbalanced._check_balance()
        assert exc.value.code == FINErrorCode.AP_UNBALANCED

    # ---- 状态标记 ----

    def test_mark_partial(self) -> None:
        ap = _build_ap().mark_partial()
        assert ap.status == VoucherStatus.PARTIAL

    def test_mark_settled(self) -> None:
        ap = _build_ap().mark_settled()
        assert ap.status == VoucherStatus.SETTLED

    def test_mark_overdue(self) -> None:
        ap = _build_ap().mark_overdue(20)
        assert ap.is_overdue is True
        assert ap.overdue_days == 20

    def test_red_voucher(self) -> None:
        ap = _build_ap().red_voucher()
        assert ap.status == VoucherStatus.RED

    def test_zero_payment_keeps_open(self) -> None:
        # 付款 0 元，状态保持 OPEN（覆盖 else 分支）
        ap = _build_ap().apply_payment(Money(Decimal("0.00")))
        assert ap.status == VoucherStatus.OPEN
        assert ap.paid_amount.amount == Decimal("0.00")

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_ap()
        updated = original.apply_payment(Money(Decimal("100.00")))
        assert original.paid_amount.amount == Decimal("0.00")
        assert updated.paid_amount.amount == Decimal("100.00")
        assert original is not updated