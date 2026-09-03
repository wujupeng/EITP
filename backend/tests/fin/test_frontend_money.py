"""红线测试 T15-14 - 前端金额约定：Money 值对象序列化与前端契约。

验证 EITP-FIN-001 的前后端金额一致性红线：
- Money.__str__ 返回 "{amount} {currency}" 格式（前端解析约定）
- Money.from_str 从字符串构建（前端输入约定）
- Money 序列化为 JSON 时 amount 为字符串（避免 float 精度丢失）
- Money 精度始终 2 位小数（前端显示约定）
- Money 比较运算符可用于前端排序/过滤
- Money 守恒校验可用于前端余额校验
"""

from __future__ import annotations

from decimal import Decimal
from json import dumps

import pytest

from app.domain.fin.value_objects.money import Money


class TestMoneyStringFormat:
    """前端约定：str(Money) == "{amount} {currency}"。"""

    def test_str_format_cny(self) -> None:
        m = Money(Decimal("100.00"))
        assert str(m) == "100.00 CNY"

    def test_str_format_usd(self) -> None:
        m = Money(Decimal("99.99"), "USD")
        assert str(m) == "99.99 USD"

    def test_str_format_zero(self) -> None:
        m = Money.zero()
        assert str(m) == "0.00 CNY"

    def test_str_format_large_amount(self) -> None:
        m = Money(Decimal("999999999.99"))
        assert str(m) == "999999999.99 CNY"

    def test_str_format_small_amount(self) -> None:
        m = Money(Decimal("0.01"))
        assert str(m) == "0.01 CNY"

    def test_str_format_always_two_decimal_places(self) -> None:
        """前端依赖金额始终有 2 位小数。"""
        m1 = Money(Decimal("100"))
        m2 = Money(Decimal("100.1"))
        m3 = Money(Decimal("100.10"))
        assert str(m1) == "100.00 CNY"
        assert str(m2) == "100.10 CNY"
        assert str(m3) == "100.10 CNY"


class TestMoneyFromString:
    """前端约定：Money.from_str 从字符串构建。"""

    def test_from_str_basic(self) -> None:
        m = Money.from_str("100.00")
        assert m.amount == Decimal("100.00")
        assert m.currency == "CNY"

    def test_from_str_with_currency(self) -> None:
        m = Money.from_str("50.00", "USD")
        assert m.amount == Decimal("50.00")
        assert m.currency == "USD"

    def test_from_str_integer(self) -> None:
        m = Money.from_str("100")
        assert m.amount == Decimal("100.00")

    def test_from_str_round_trip(self) -> None:
        """str → from_str → str 往返一致。"""
        original = Money(Decimal("1234.56"), "CNY")
        s = str(original)
        # 解析 "1234.56 CNY"
        amount_str, currency = s.rsplit(" ", 1)
        restored = Money.from_str(amount_str, currency)
        assert restored == original

    def test_from_str_large_amount(self) -> None:
        m = Money.from_str("999999999.99")
        assert m.amount == Decimal("999999999.99")


class TestMoneyJsonSerialization:
    """前端约定：JSON 序列化时 amount 为字符串。"""

    def test_amount_serialized_as_string(self) -> None:
        """前端收到的 amount 应为字符串，避免 JS float 精度丢失。"""
        m = Money(Decimal("100.00"))
        data = {"amount": str(m.amount), "currency": m.currency}
        json_str = dumps(data)
        assert '"amount": "100.00"' in json_str
        assert '"currency": "CNY"' in json_str

    def test_large_amount_not_corrupted_by_json(self) -> None:
        """大金额 JSON 序列化不丢失精度。"""
        m = Money(Decimal("9999999999.99"))
        data = {"amount": str(m.amount), "currency": m.currency}
        json_str = dumps(data)
        parsed = __import__("json").loads(json_str)
        assert parsed["amount"] == "9999999999.99"

    def test_zero_serialization(self) -> None:
        m = Money.zero()
        data = {"amount": str(m.amount), "currency": m.currency}
        json_str = dumps(data)
        assert '"amount": "0.00"' in json_str

    def test_currency_always_in_json(self) -> None:
        m = Money(Decimal("100.00"), "USD")
        data = {"amount": str(m.amount), "currency": m.currency}
        assert data["currency"] == "USD"


class TestMoneyPrecisionForFrontend:
    """前端约定：金额精度始终 2 位小数。"""

    def test_integer_quantized_to_two_places(self) -> None:
        m = Money(Decimal("100"))
        assert str(m.amount) == "100.00"

    def test_one_decimal_quantized_to_two_places(self) -> None:
        m = Money(Decimal("100.1"))
        assert str(m.amount) == "100.10"

    def test_two_decimal_preserved(self) -> None:
        m = Money(Decimal("100.99"))
        assert str(m.amount) == "100.99"

    def test_addition_preserves_precision(self) -> None:
        a = Money(Decimal("100.00"))
        b = Money(Decimal("0.05"))
        result = a.add(b)
        assert str(result.amount) == "100.05"

    def test_subtraction_preserves_precision(self) -> None:
        a = Money(Decimal("100.00"))
        b = Money(Decimal("0.01"))
        result = a.subtract(b)
        assert str(result.amount) == "99.99"

    def test_multiply_preserves_precision(self) -> None:
        m = Money(Decimal("100.00"))
        result = m.multiply(Decimal("0.13"))
        assert str(result.amount) == "13.00"


class TestMoneyComparisonForFrontend:
    """前端约定：比较运算符用于排序/过滤。"""

    def test_less_than(self) -> None:
        assert Money(Decimal("100.00")) < Money(Decimal("200.00"))

    def test_less_than_or_equal(self) -> None:
        assert Money(Decimal("100.00")) <= Money(Decimal("100.00"))
        assert Money(Decimal("99.99")) <= Money(Decimal("100.00"))

    def test_greater_than(self) -> None:
        assert Money(Decimal("200.00")) > Money(Decimal("100.00"))

    def test_greater_than_or_equal(self) -> None:
        assert Money(Decimal("100.00")) >= Money(Decimal("100.00"))
        assert Money(Decimal("100.01")) >= Money(Decimal("100.00"))

    def test_equal(self) -> None:
        assert Money(Decimal("100.00")) == Money(Decimal("100.00"))

    def test_not_equal(self) -> None:
        assert Money(Decimal("100.00")) != Money(Decimal("200.00"))

    def test_equal_different_currency_not_equal(self) -> None:
        cny = Money(Decimal("100.00"), "CNY")
        usd = Money(Decimal("100.00"), "USD")
        assert cny != usd

    def test_sorting_by_amount(self) -> None:
        amounts = [
            Money(Decimal("300.00")),
            Money(Decimal("100.00")),
            Money(Decimal("200.00")),
        ]
        sorted_amounts = sorted(amounts)
        assert sorted_amounts[0] == Money(Decimal("100.00"))
        assert sorted_amounts[1] == Money(Decimal("200.00"))
        assert sorted_amounts[2] == Money(Decimal("300.00"))


class TestMoneyConservationForFrontend:
    """前端约定：守恒校验用于余额显示。"""

    def test_ar_balance_display(self) -> None:
        """前端显示：应收余额 = 应收 - 已收。"""
        receivable = Money(Decimal("10000.00"))
        received = Money(Decimal("3000.00"))
        balance = receivable.subtract(received)
        assert balance == Money(Decimal("7000.00"))
        assert Money.is_conserved(receivable, received, balance)

    def test_ap_balance_display(self) -> None:
        """前端显示：应付余额 = 应付 - 已付。"""
        payable = Money(Decimal("5000.00"))
        paid = Money(Decimal("2000.00"))
        balance = payable.subtract(paid)
        assert balance == Money(Decimal("3000.00"))
        assert Money.is_ap_conserved(payable, paid, balance)

    def test_progress_bar_calculation(self) -> None:
        """前端进度条：已收 / 应收。"""
        receivable = Money(Decimal("10000.00"))
        received = Money(Decimal("2500.00"))
        ratio = received.amount / receivable.amount
        assert ratio == Decimal("0.25")

    def test_zero_balance_display(self) -> None:
        """前端显示：全额收清时余额为 0。"""
        receivable = Money(Decimal("1000.00"))
        received = Money(Decimal("1000.00"))
        balance = receivable.subtract(received)
        assert balance == Money.zero()
        assert str(balance) == "0.00 CNY"


class TestMoneyEdgeCasesForFrontend:
    """前端约定：边界值处理。"""

    def test_one_cent(self) -> None:
        m = Money(Decimal("0.01"))
        assert str(m) == "0.01 CNY"

    def test_max_two_decimal(self) -> None:
        m = Money(Decimal("0.99"))
        assert str(m) == "0.99 CNY"

    def test_zero_is_falsy_amount(self) -> None:
        m = Money.zero()
        assert m.amount == Decimal("0.00")

    def test_add_zero_no_change(self) -> None:
        m = Money(Decimal("100.00"))
        assert m.add(Money.zero()) == m

    def test_currency_in_str(self) -> None:
        """前端从 str(Money) 中提取币种。"""
        m = Money(Decimal("100.00"), "USD")
        s = str(m)
        _, currency = s.rsplit(" ", 1)
        assert currency == "USD"

    def test_hashable_for_frontend_dedup(self) -> None:
        """Money 可哈希，用于前端去重。"""
        m1 = Money(Decimal("100.00"))
        m2 = Money(Decimal("100.00"))
        assert hash(m1) == hash(m2)
        assert m1 in {m2}