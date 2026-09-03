"""Money 值对象单元测试 - Decimal 高精度运算与不变量守卫。

覆盖：
- Decimal 加/减/乘算术与运算符重载
- float 输入拒绝 (MONEY_FLOAT_FORBIDDEN)
- 精度损失检测 (MONEY_PRECISION_LOSS) - 超 2 位小数 / 不可转换
- 负数金额拒绝 (MONEY_NEGATIVE_FORBIDDEN)
- 货币不匹配 (MONEY_CURRENCY_MISMATCH)
- is_conserved() / is_ap_conserved() 守恒校验
- from_str / zero 工厂、比较运算、哈希、字符串表示
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.money import Money


class MoneyTest:
    """Money 值对象 Decimal 算术与不变量测试。"""

    # ---- 构造与工厂 ----

    def test_construct_with_decimal(self) -> None:
        m = Money(Decimal("100.50"), "CNY")
        assert m.amount == Decimal("100.50")
        assert m.currency == "CNY"

    def test_default_currency_is_cny(self) -> None:
        m = Money(Decimal("10"))
        assert m.currency == "CNY"

    def test_from_str_factory(self) -> None:
        m = Money.from_str("123.45", "USD")
        assert m.amount == Decimal("123.45")
        assert m.currency == "USD"

    def test_zero_factory(self) -> None:
        z = Money.zero("CNY")
        assert z.amount == Decimal("0")
        assert z.currency == "CNY"

    def test_str_input_coerced_to_decimal(self) -> None:
        # 非 Decimal 非 float 输入（如 str）应被转换为 Decimal
        m = Money("88.88")  # type: ignore[arg-type]
        assert m.amount == Decimal("88.88")

    def test_int_input_coerced_to_decimal(self) -> None:
        m = Money(50)  # type: ignore[arg-type]
        assert m.amount == Decimal("50")

    # ---- float 拒绝 ----

    def test_float_amount_rejected(self) -> None:
        with pytest.raises(FINError) as exc:
            Money(1.23)  # type: ignore[arg-type]
        assert exc.value.code == FINErrorCode.MONEY_FLOAT_FORBIDDEN

    def test_float_factor_in_multiply_rejected(self) -> None:
        m = Money(Decimal("100"))
        with pytest.raises(FINError) as exc:
            m.multiply(1.5)  # type: ignore[arg-type]
        assert exc.value.code == FINErrorCode.MONEY_FLOAT_FORBIDDEN

    # ---- 精度损失 ----

    def test_precision_exceeds_two_decimals_rejected(self) -> None:
        with pytest.raises(FINError) as exc:
            Money(Decimal("1.234"))
        assert exc.value.code == FINErrorCode.MONEY_PRECISION_LOSS

    def test_unconvertible_input_rejected_as_precision_loss(self) -> None:
        # 无法转换为 Decimal 的输入触发 MONEY_PRECISION_LOSS
        with pytest.raises(FINError) as exc:
            Money("not-a-number")  # type: ignore[arg-type]
        assert exc.value.code == FINErrorCode.MONEY_PRECISION_LOSS

    def test_quantize_to_two_decimals(self) -> None:
        # 整数金额应被量化为 2 位小数表示
        m = Money(Decimal("100"))
        assert m.amount == Decimal("100.00")

    # ---- 负数拒绝 ----

    def test_negative_amount_rejected(self) -> None:
        with pytest.raises(FINError) as exc:
            Money(Decimal("-1"))
        assert exc.value.code == FINErrorCode.MONEY_NEGATIVE_FORBIDDEN

    def test_subtract_to_negative_rejected(self) -> None:
        big = Money(Decimal("100"))
        small = Money(Decimal("30"))
        with pytest.raises(FINError) as exc:
            small.subtract(big)
        assert exc.value.code == FINErrorCode.MONEY_NEGATIVE_FORBIDDEN

    # ---- 货币不匹配 ----

    def test_currency_mismatch_on_add(self) -> None:
        cny = Money(Decimal("100"), "CNY")
        usd = Money(Decimal("50"), "USD")
        with pytest.raises(FINError) as exc:
            cny.add(usd)
        assert exc.value.code == FINErrorCode.MONEY_CURRENCY_MISMATCH

    def test_currency_mismatch_on_subtract(self) -> None:
        cny = Money(Decimal("100"), "CNY")
        usd = Money(Decimal("50"), "USD")
        with pytest.raises(FINError) as exc:
            cny.subtract(usd)
        assert exc.value.code == FINErrorCode.MONEY_CURRENCY_MISMATCH

    # ---- 算术运算 ----

    def test_add(self) -> None:
        a = Money(Decimal("100.50"))
        b = Money(Decimal("200.25"))
        result = a.add(b)
        assert result.amount == Decimal("300.75")
        assert result.currency == "CNY"

    def test_subtract(self) -> None:
        a = Money(Decimal("300.75"))
        b = Money(Decimal("100.50"))
        result = a.subtract(b)
        assert result.amount == Decimal("200.25")

    def test_multiply_by_int(self) -> None:
        m = Money(Decimal("100.50"))
        result = m.multiply(3)
        assert result.amount == Decimal("301.50")

    def test_multiply_by_decimal(self) -> None:
        m = Money(Decimal("100.00"))
        result = m.multiply(Decimal("0.13"))
        assert result.amount == Decimal("13.00")

    def test_operator_add(self) -> None:
        result = Money(Decimal("10")) + Money(Decimal("20"))
        assert result.amount == Decimal("30.00")

    def test_operator_sub(self) -> None:
        result = Money(Decimal("50")) - Money(Decimal("20"))
        assert result.amount == Decimal("30.00")

    def test_operator_mul(self) -> None:
        result = Money(Decimal("10")) * 5
        assert result.amount == Decimal("50.00")

    # ---- 比较运算 ----

    def test_equality_same_amount_and_currency(self) -> None:
        assert Money(Decimal("100"), "CNY") == Money(Decimal("100"), "CNY")

    def test_inequality_different_amount(self) -> None:
        assert Money(Decimal("100")) != Money(Decimal("200"))

    def test_inequality_different_currency(self) -> None:
        assert Money(Decimal("100"), "CNY") != Money(Decimal("100"), "USD")

    def test_equality_with_non_money_returns_not_implemented(self) -> None:
        assert (Money(Decimal("100")) == 100) is False

    def test_less_than(self) -> None:
        assert Money(Decimal("50")) < Money(Decimal("100"))

    def test_less_equal(self) -> None:
        assert Money(Decimal("100")) <= Money(Decimal("100"))

    def test_greater_than(self) -> None:
        assert Money(Decimal("100")) > Money(Decimal("50"))

    def test_greater_equal(self) -> None:
        assert Money(Decimal("100")) >= Money(Decimal("100"))

    def test_comparison_currency_mismatch_raises(self) -> None:
        with pytest.raises(FINError) as exc:
            _ = Money(Decimal("100"), "CNY") < Money(Decimal("50"), "USD")
        assert exc.value.code == FINErrorCode.MONEY_CURRENCY_MISMATCH

    # ---- 哈希与字符串 ----

    def test_hash_consistent_with_equality(self) -> None:
        a = Money(Decimal("100"), "CNY")
        b = Money(Decimal("100"), "CNY")
        assert hash(a) == hash(b)

    def test_str_representation(self) -> None:
        m = Money(Decimal("100.50"), "CNY")
        assert str(m) == "100.50 CNY"

    # ---- 守恒校验 ----

    def test_is_conserved_balanced(self) -> None:
        receivable = Money(Decimal("1000"))
        received = Money(Decimal("300"))
        unreceived = Money(Decimal("700"))
        assert Money.is_conserved(receivable, received, unreceived) is True

    def test_is_conserved_unbalanced(self) -> None:
        receivable = Money(Decimal("1000"))
        received = Money(Decimal("300"))
        unreceived = Money(Decimal("800"))
        assert Money.is_conserved(receivable, received, unreceived) is False

    def test_is_ap_conserved_balanced(self) -> None:
        payable = Money(Decimal("2000"))
        paid = Money(Decimal("500"))
        unpaid = Money(Decimal("1500"))
        assert Money.is_ap_conserved(payable, paid, unpaid) is True

    def test_is_ap_conserved_unbalanced(self) -> None:
        payable = Money(Decimal("2000"))
        paid = Money(Decimal("500"))
        unpaid = Money(Decimal("1400"))
        assert Money.is_ap_conserved(payable, paid, unpaid) is False

    def test_frozen_dataclass_immutable(self) -> None:
        m = Money(Decimal("100"))
        with pytest.raises(Exception):
            m.amount = Decimal("200")  # type: ignore[misc]