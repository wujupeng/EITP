"""GLVoucherAggregate 单元测试 - 借贷平衡 + 期间锁定 + 红冲。

覆盖：
- 借贷平衡校验 is_balanced / post (GL_UNBALANCED)
- 期间关闭锁定 (GL_PERIOD_CLOSED)
- 红冲凭证生成（借贷互换）
- close_period 期间关闭
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.aggregates.gl_voucher_aggregate import (
    GLVoucherAggregate,
    GLVoucherLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.money import Money


def _balanced_lines() -> list[GLVoucherLine]:
    return [
        GLVoucherLine(
            line_no=1,
            account_code="1001",
            debit_amount=Money(Decimal("1000.00")),
            credit_amount=Money(Decimal("0.00")),
        ),
        GLVoucherLine(
            line_no=2,
            account_code="2001",
            debit_amount=Money(Decimal("0.00")),
            credit_amount=Money(Decimal("1000.00")),
        ),
    ]


def _unbalanced_lines() -> list[GLVoucherLine]:
    return [
        GLVoucherLine(
            line_no=1,
            account_code="1001",
            debit_amount=Money(Decimal("1000.00")),
            credit_amount=Money(Decimal("0.00")),
        ),
        GLVoucherLine(
            line_no=2,
            account_code="2001",
            debit_amount=Money(Decimal("0.00")),
            credit_amount=Money(Decimal("800.00")),
        ),
    ]


def _build_gl(lines: list[GLVoucherLine] | None = None) -> GLVoucherAggregate:
    return GLVoucherAggregate.create(
        voucher_no="GL-001",
        voucher_date=date(2026, 9, 1),
        summary="测试凭证",
        period="2026-09",
        tenant_id=uuid4(),
        lines=lines if lines is not None else _balanced_lines(),
    )


class GLVoucherAggregateTest:
    """GLVoucherAggregate 借贷平衡与期间锁定测试。"""

    def test_create_initial_period_open(self) -> None:
        gl = _build_gl()
        assert gl.is_period_closed is False
        assert gl.red_original_voucher_no is None

    # ---- 借贷平衡 ----

    def test_is_balanced_true(self) -> None:
        gl = _build_gl()
        assert gl.is_balanced() is True

    def test_is_balanced_false(self) -> None:
        gl = _build_gl(_unbalanced_lines())
        assert gl.is_balanced() is False

    def test_post_balanced_succeeds(self) -> None:
        gl = _build_gl().post()
        assert gl.is_balanced() is True

    def test_post_unbalanced_rejected(self) -> None:
        gl = _build_gl(_unbalanced_lines())
        with pytest.raises(FINError) as exc:
            gl.post()
        assert exc.value.code == FINErrorCode.GL_UNBALANCED

    # ---- 期间锁定 ----

    def test_close_period(self) -> None:
        gl = _build_gl().close_period()
        assert gl.is_period_closed is True

    def test_post_after_period_closed_rejected(self) -> None:
        gl = _build_gl().close_period()
        with pytest.raises(FINError) as exc:
            gl.post()
        assert exc.value.code == FINErrorCode.GL_PERIOD_CLOSED

    def test_close_period_twice_rejected(self) -> None:
        gl = _build_gl().close_period()
        with pytest.raises(FINError) as exc:
            gl.close_period()
        assert exc.value.code == FINErrorCode.GL_PERIOD_CLOSED

    def test_red_voucher_after_period_closed_rejected(self) -> None:
        gl = _build_gl().close_period()
        with pytest.raises(FINError) as exc:
            gl.red_voucher("GL-RED-001")
        assert exc.value.code == FINErrorCode.GL_PERIOD_CLOSED

    # ---- 红冲凭证 ----

    def test_red_voucher_swaps_debit_credit(self) -> None:
        gl = _build_gl()
        red = gl.red_voucher("GL-RED-001")
        assert red.voucher_no == "GL-RED-001"
        assert red.red_original_voucher_no == "GL-001"
        assert red.summary == "RED: 测试凭证"
        # 借贷互换：原借 1000/贷 0 → 红冲借 0/贷 1000
        assert red.lines[0].debit_amount.amount == Decimal("0.00")
        assert red.lines[0].credit_amount.amount == Decimal("1000.00")
        assert red.lines[1].debit_amount.amount == Decimal("1000.00")
        assert red.lines[1].credit_amount.amount == Decimal("0.00")

    def test_red_voucher_remains_balanced(self) -> None:
        gl = _build_gl()
        red = gl.red_voucher("GL-RED-001")
        assert red.is_balanced() is True

    def test_red_voucher_period_open(self) -> None:
        gl = _build_gl()
        red = gl.red_voucher("GL-RED-001")
        assert red.is_period_closed is False

    # ---- 空行 ----

    def test_empty_lines_is_balanced(self) -> None:
        gl = _build_gl(lines=[])
        # 空行借貸均为 0，视为平衡
        assert gl.is_balanced() is True

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_gl()
        closed = original.close_period()
        assert original.is_period_closed is False
        assert closed.is_period_closed is True
        assert original is not closed