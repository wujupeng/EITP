"""红线测试 T15-10 - 金额一致性：Money 守恒律与精度约束。

验证 EITP-FIN-001 的金额一致性红线：
- 应收 = 已收 + 未收（AR 守恒）
- 应付 = 已付 + 未付（AP 守恒）
- Money 强制 Decimal，禁止 float
- Money 禁止负数
- Money 精度最多 2 位小数
- Money 币种必须匹配
- 运算保持守恒
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.money import Money


class TestMoneyFloatForbidden:
    """红线 4：Money 禁止 float。"""

    def test_float_amount_rejected(self) -> None:
        with pytest.raises(FINError) as exc_info:
            Money(1.0)  # type: ignore[arg-type]
        assert exc_info.value.code == FINErrorCode.MONEY_FLOAT_FORBIDDEN

    def test_float_in_string_rejected_at_precision(self) -> None:
        """字符串 '1.001' 超精度被拒。"""
        with pytest.raises(FINError) as exc_info:
            Money(Decimal("1.001"))
        assert exc_info.value.code == FINErrorCode.MONEY_PRECISION_LOSS

    def test_multiply_with_float_factor_rejected(self) -> None:
        m = Money(Decimal("100.00"))
        with pytest.raises(FINError) as exc_info:
            m.multiply(0.13)  # type: ignore[arg-type]
        assert exc_info.value.code == FINErrorCode.MONEY_FLOAT_FORBIDDEN

    def test_int_factor_allowed(self) -> None:
        m = Money(Decimal("100.00"))
        result = m.multiply(3)
        assert result == Money(Decimal("300.00"))

    def test_decimal_factor_allowed(self) -> None:
        m = Money(Decimal("100.00"))
        result = m.multiply(Decimal("0.13"))
        assert result == Money(Decimal("13.00"))


class TestMoneyNegativeForbidden:
    """红线 4：Money 禁止负数。"""

    def test_negative_decimal_rejected(self) -> None:
        with pytest.raises(FINError) as exc_info:
            Money(Decimal("-1.00"))
        assert exc_info.value.code == FINErrorCode.MONEY_NEGATIVE_FORBIDDEN

    def test_negative_string_rejected(self) -> None:
        with pytest.raises(FINError) as exc_info:
            Money.from_str("-100.00")
        assert exc_info.value.code == FINErrorCode.MONEY_NEGATIVE_FORBIDDEN

    def test_zero_allowed(self) -> None:
        m = Money.zero()
        assert m.amount == Decimal("0.00")

    def test_subtraction_resulting_negative_rejected(self) -> None:
        big = Money(Decimal("100.00"))
        small = Money(Decimal("50.00"))
        with pytest.raises(FINError) as exc_info:
            small.subtract(big)
        assert exc_info.value.code == FINErrorCode.MONEY_NEGATIVE_FORBIDDEN


class TestMoneyPrecisionConstraint:
    """红线 4：Money 精度最多 2 位小数。"""

    def test_two_decimal_places_allowed(self) -> None:
        m = Money(Decimal("100.99"))
        assert m.amount == Decimal("100.99")

    def test_three_decimal_places_rejected(self) -> None:
        with pytest.raises(FINError) as exc_info:
            Money(Decimal("100.999"))
        assert exc_info.value.code == FINErrorCode.MONEY_PRECISION_LOSS

    def test_quantized_to_two_places(self) -> None:
        m = Money(Decimal("100.1"))
        assert m.amount == Decimal("100.10")

    def test_zero_decimal_places_allowed(self) -> None:
        m = Money(Decimal("100"))
        assert m.amount == Decimal("100.00")

    def test_from_str_precision(self) -> None:
        m = Money.from_str("1234.56")
        assert m.amount == Decimal("1234.56")


class TestMoneyCurrencyMismatch:
    """红线 4：Money 币种必须匹配。"""

    def test_add_different_currency_rejected(self) -> None:
        cny = Money(Decimal("100.00"), "CNY")
        usd = Money(Decimal("50.00"), "USD")
        with pytest.raises(FINError) as exc_info:
            cny.add(usd)
        assert exc_info.value.code == FINErrorCode.MONEY_CURRENCY_MISMATCH

    def test_subtract_different_currency_rejected(self) -> None:
        cny = Money(Decimal("100.00"), "CNY")
        usd = Money(Decimal("50.00"), "USD")
        with pytest.raises(FINError) as exc_info:
            cny.subtract(usd)
        assert exc_info.value.code == FINErrorCode.MONEY_CURRENCY_MISMATCH

    def test_compare_different_currency_rejected(self) -> None:
        cny = Money(Decimal("100.00"), "CNY")
        usd = Money(Decimal("50.00"), "USD")
        with pytest.raises(FINError):
            cny < usd  # noqa: B015

    def test_same_currency_add_succeeds(self) -> None:
        a = Money(Decimal("100.00"), "CNY")
        b = Money(Decimal("50.00"), "CNY")
        result = a.add(b)
        assert result == Money(Decimal("150.00"), "CNY")


class TestARConservation:
    """红线 4：应收 = 已收 + 未收。"""

    def test_conserved_when_balanced(self) -> None:
        receivable = Money(Decimal("1000.00"))
        received = Money(Decimal("300.00"))
        unreceived = Money(Decimal("700.00"))
        assert Money.is_conserved(receivable, received, unreceived)

    def test_not_conserved_when_imbalanced(self) -> None:
        receivable = Money(Decimal("1000.00"))
        received = Money(Decimal("300.00"))
        unreceived = Money(Decimal("800.00"))
        assert not Money.is_conserved(receivable, received, unreceived)

    def test_conserved_at_zero_received(self) -> None:
        receivable = Money(Decimal("1000.00"))
        received = Money.zero()
        unreceived = Money(Decimal("1000.00"))
        assert Money.is_conserved(receivable, received, unreceived)

    def test_conserved_at_full_received(self) -> None:
        receivable = Money(Decimal("1000.00"))
        received = Money(Decimal("1000.00"))
        unreceived = Money.zero()
        assert Money.is_conserved(receivable, received, unreceived)

    def test_conservation_after_partial_receipt(self) -> None:
        receivable = Money(Decimal("10000.00"))
        received = Money(Decimal("3500.00"))
        unreceived = receivable.subtract(received)
        assert Money.is_conserved(receivable, received, unreceived)

    def test_conservation_with_multiple_receipts(self) -> None:
        receivable = Money(Decimal("10000.00"))
        r1 = Money(Decimal("1000.00"))
        r2 = Money(Decimal("2000.00"))
        r3 = Money(Decimal("3000.00"))
        received = r1.add(r2).add(r3)
        unreceived = receivable.subtract(received)
        assert Money.is_conserved(receivable, received, unreceived)
        assert received == Money(Decimal("6000.00"))
        assert unreceived == Money(Decimal("4000.00"))


class TestAPConservation:
    """红线 4：应付 = 已付 + 未付。"""

    def test_conserved_when_balanced(self) -> None:
        payable = Money(Decimal("5000.00"))
        paid = Money(Decimal("2000.00"))
        unpaid = Money(Decimal("3000.00"))
        assert Money.is_ap_conserved(payable, paid, unpaid)

    def test_not_conserved_when_imbalanced(self) -> None:
        payable = Money(Decimal("5000.00"))
        paid = Money(Decimal("2000.00"))
        unpaid = Money(Decimal("4000.00"))
        assert not Money.is_ap_conserved(payable, paid, unpaid)

    def test_conserved_at_zero_paid(self) -> None:
        payable = Money(Decimal("5000.00"))
        paid = Money.zero()
        unpaid = Money(Decimal("5000.00"))
        assert Money.is_ap_conserved(payable, paid, unpaid)

    def test_conserved_at_full_paid(self) -> None:
        payable = Money(Decimal("5000.00"))
        paid = Money(Decimal("5000.00"))
        unpaid = Money.zero()
        assert Money.is_ap_conserved(payable, paid, unpaid)

    def test_conservation_after_partial_payment(self) -> None:
        payable = Money(Decimal("8000.00"))
        paid = Money(Decimal("2500.00"))
        unpaid = payable.subtract(paid)
        assert Money.is_ap_conserved(payable, paid, unpaid)

    def test_conservation_with_multiple_payments(self) -> None:
        payable = Money(Decimal("8000.00"))
        p1 = Money(Decimal("1000.00"))
        p2 = Money(Decimal("1500.00"))
        paid = p1.add(p2)
        unpaid = payable.subtract(paid)
        assert Money.is_ap_conserved(payable, paid, unpaid)
        assert paid == Money(Decimal("2500.00"))
        assert unpaid == Money(Decimal("5500.00"))


class TestMoneyArithmeticConsistency:
    """红线 4：Money 运算保持一致性。"""

    def test_add_then_subtract_returns_original(self) -> None:
        original = Money(Decimal("1000.00"))
        delta = Money(Decimal("300.00"))
        result = original.add(delta).subtract(delta)
        assert result == original

    def test_add_is_commutative(self) -> None:
        a = Money(Decimal("100.00"))
        b = Money(Decimal("200.00"))
        assert a.add(b) == b.add(a)

    def test_add_is_associative(self) -> None:
        a = Money(Decimal("100.00"))
        b = Money(Decimal("200.00"))
        c = Money(Decimal("300.00"))
        assert a.add(b).add(c) == b.add(c).add(a)

    def test_multiply_then_compare(self) -> None:
        price = Money(Decimal("100.00"))
        qty = Decimal("3")
        total = price.multiply(qty)
        assert total == Money(Decimal("300.00"))

    def test_zero_is_identity_for_add(self) -> None:
        m = Money(Decimal("500.00"))
        assert m.add(Money.zero()) == m

    def test_subtract_self_yields_zero(self) -> None:
        m = Money(Decimal("500.00"))
        assert m.subtract(m) == Money.zero()

    def test_operator_overloading_consistency(self) -> None:
        a = Money(Decimal("100.00"))
        b = Money(Decimal("50.00"))
        assert a + b == Money(Decimal("150.00"))
        assert a - b == Money(Decimal("50.00"))
        assert a * 2 == Money(Decimal("200.00"))

    def test_comparison_operators(self) -> None:
        a = Money(Decimal("100.00"))
        b = Money(Decimal("200.00"))
        assert a < b
        assert a <= b
        assert b > a
        assert b >= a
        assert a != b
        assert a == Money(Decimal("100.00"))