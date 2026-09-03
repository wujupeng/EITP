"""ARVoucherAggregate 单元测试 - 金额守恒 + 收款核销。

覆盖：
- 创建初始守恒 receivable = received + unreceived
- apply_receipt 部分收款后守恒保持
- apply_receipt 全额收款后状态 SETTLED
- 收款超额拒绝 (RECEIPT_WRITEOFF_EXCEED)
- AR_UNBALANCED 拒绝（构造期手动构造不平衡）
- mark_partial / mark_settled / mark_overdue / red_voucher
"""

from __future__ import annotations

from dataclasses import replace as dataclass_replace
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.aggregates.ar_voucher_aggregate import ARVoucherAggregate
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import VoucherStatus
from app.domain.fin.value_objects.money import Money


def _build_ar() -> ARVoucherAggregate:
    return ARVoucherAggregate.create(
        voucher_no="AR-001",
        business_ref_type="SETTLEMENT",
        business_ref_id="ST-001",
        receivable_amount=Money(Decimal("1000.00")),
        tenant_id=uuid4(),
        credit_period_days=30,
    )


class ARVoucherAggregateTest:
    """ARVoucherAggregate 金额守恒与收款核销测试。"""

    def test_create_initial_balance_conserved(self) -> None:
        ar = _build_ar()
        assert ar.receivable_amount.amount == Decimal("1000.00")
        assert ar.received_amount.amount == Decimal("0.00")
        assert ar.unreceived_amount.amount == Decimal("1000.00")
        assert ar.status == VoucherStatus.OPEN
        # 守恒：receivable == received + unreceived
        assert Money.is_conserved(ar.receivable_amount, ar.received_amount, ar.unreceived_amount)

    # ---- apply_receipt ----

    def test_partial_receipt_keeps_conservation(self) -> None:
        ar = _build_ar().apply_receipt(Money(Decimal("300.00")))
        assert ar.received_amount.amount == Decimal("300.00")
        assert ar.unreceived_amount.amount == Decimal("700.00")
        assert ar.status == VoucherStatus.PARTIAL
        assert Money.is_conserved(ar.receivable_amount, ar.received_amount, ar.unreceived_amount)

    def test_full_receipt_settles(self) -> None:
        ar = _build_ar().apply_receipt(Money(Decimal("1000.00")))
        assert ar.received_amount.amount == Decimal("1000.00")
        assert ar.unreceived_amount.amount == Decimal("0.00")
        assert ar.status == VoucherStatus.SETTLED

    def test_multi_partial_receipts(self) -> None:
        ar = _build_ar().apply_receipt(Money(Decimal("300.00"))).apply_receipt(Money(Decimal("500.00")))
        assert ar.received_amount.amount == Decimal("800.00")
        assert ar.unreceived_amount.amount == Decimal("200.00")
        assert ar.status == VoucherStatus.PARTIAL

    # ---- 收款超额拒绝 ----

    def test_receipt_exceed_unreceived_rejected(self) -> None:
        ar = _build_ar()
        with pytest.raises(FINError) as exc:
            ar.apply_receipt(Money(Decimal("1001.00")))
        assert exc.value.code == FINErrorCode.RECEIPT_WRITEOFF_EXCEED

    def test_receipt_exceed_after_partial_rejected(self) -> None:
        ar = _build_ar().apply_receipt(Money(Decimal("800.00")))
        with pytest.raises(FINError) as exc:
            ar.apply_receipt(Money(Decimal("300.00")))
        assert exc.value.code == FINErrorCode.RECEIPT_WRITEOFF_EXCEED

    # ---- AR_UNBALANCED 拒绝 ----

    def test_unbalanced_construction_raises_on_apply(self) -> None:
        # 手动构造不平衡凭证：receivable=1000, received=100, unreceived=700（不守恒）
        base = _build_ar()
        unbalanced = dataclass_replace(
            base,
            received_amount=Money(Decimal("100.00")),
            unreceived_amount=Money(Decimal("700.00")),
        )
        # apply_receipt 内部会校验操作后守恒，此处构造已不平衡，
        # 但 apply_receipt 仅校验新守恒；用 _check_balance 直接触发
        with pytest.raises(FINError) as exc:
            unbalanced._check_balance()
        assert exc.value.code == FINErrorCode.AR_UNBALANCED

    # ---- 状态标记 ----

    def test_mark_partial(self) -> None:
        ar = _build_ar().mark_partial()
        assert ar.status == VoucherStatus.PARTIAL

    def test_mark_settled(self) -> None:
        ar = _build_ar().mark_settled()
        assert ar.status == VoucherStatus.SETTLED

    def test_mark_overdue(self) -> None:
        ar = _build_ar().mark_overdue(15)
        assert ar.is_overdue is True
        assert ar.overdue_days == 15

    def test_red_voucher(self) -> None:
        ar = _build_ar().red_voucher()
        assert ar.status == VoucherStatus.RED

    def test_zero_receipt_keeps_open(self) -> None:
        # 收款 0 元，状态保持 OPEN（覆盖 else 分支）
        ar = _build_ar().apply_receipt(Money(Decimal("0.00")))
        assert ar.status == VoucherStatus.OPEN
        assert ar.received_amount.amount == Decimal("0.00")

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_ar()
        updated = original.apply_receipt(Money(Decimal("100.00")))
        assert original.received_amount.amount == Decimal("0.00")
        assert updated.received_amount.amount == Decimal("100.00")
        assert original is not updated