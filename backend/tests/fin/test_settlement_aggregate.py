"""SettlementAggregate 单元测试 - 5 态状态机 + Decimal 金额计算。

覆盖：
- DRAFT→CONFIRMED→SETTLED→CLOSED 主路径
- DRAFT→CANCELLED / CONFIRMED→CANCELLED 分支
- 非法状态转换拒绝 (SETTLEMENT_INVALID_TRANSITION)
- 空明细拒绝 (SETTLEMENT_LINE_EMPTY)
- Decimal 含税/不含税/税额行计算
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.aggregates.settlement_aggregate import (
    SettlementAggregate,
    SettlementLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import SettlementStatus, SettlementType
from app.domain.fin.value_objects.money import Money


def _line(line_no: int = 1, qty: Decimal = Decimal("10")) -> SettlementLine:
    return SettlementLine(
        line_no=line_no,
        product_id="P-001",
        quantity=qty,
        tax_exclusive_unit_price=Money(Decimal("100.00")),
        tax_inclusive_unit_price=Money(Decimal("113.00")),
        tax_rate=Decimal("0.13"),
    )


def _build_settlement() -> SettlementAggregate:
    return SettlementAggregate.create(
        settlement_no="ST-001",
        settlement_type=SettlementType.PURCHASE,
        counterparty_id="CP-001",
        counterparty_type="SUPPLIER",
        lines=[_line()],
        currency="CNY",
        tenant_id=uuid4(),
    )


class SettlementAggregateTest:
    """SettlementAggregate 5 态状态机与金额计算测试。"""

    def test_create_initial_status_is_draft(self) -> None:
        s = _build_settlement()
        assert s.status == SettlementStatus.DRAFT
        assert s.settlement_no == "ST-001"

    def test_create_empty_lines_rejected(self) -> None:
        with pytest.raises(FINError) as exc:
            SettlementAggregate.create(
                settlement_no="ST-EMPTY",
                settlement_type=SettlementType.PURCHASE,
                counterparty_id="CP-001",
                counterparty_type="SUPPLIER",
                lines=[],
                currency="CNY",
                tenant_id=uuid4(),
            )
        assert exc.value.code == FINErrorCode.SETTLEMENT_LINE_EMPTY

    def test_decimal_settlement_amount_calculation(self) -> None:
        # 含税单价 113.00 * 数量 10 = 1130.00
        s = _build_settlement()
        assert s.settlement_amount.amount == Decimal("1130.00")

    def test_decimal_tax_amount_calculation(self) -> None:
        # 不含税单价 100.00 * 数量 10 * 税率 0.13 = 130.00
        s = _build_settlement()
        assert s.tax_amount.amount == Decimal("130.00")

    def test_multiple_lines_accumulate(self) -> None:
        s = SettlementAggregate.create(
            settlement_no="ST-MULTI",
            settlement_type=SettlementType.SALES,
            counterparty_id="CP-002",
            counterparty_type="CUSTOMER",
            lines=[_line(1, Decimal("10")), _line(2, Decimal("5"))],
            currency="CNY",
            tenant_id=uuid4(),
        )
        # (113 * 10) + (113 * 5) = 1695.00
        assert s.settlement_amount.amount == Decimal("1695.00")
        # (100 * 10 * 0.13) + (100 * 5 * 0.13) = 195.00
        assert s.tax_amount.amount == Decimal("195.00")

    # ---- 状态转换主路径 ----

    def test_draft_to_confirmed(self) -> None:
        s = _build_settlement().confirm()
        assert s.status == SettlementStatus.CONFIRMED

    def test_confirmed_to_settled(self) -> None:
        s = _build_settlement().confirm().mark_settled()
        assert s.status == SettlementStatus.SETTLED

    def test_settled_to_closed(self) -> None:
        s = _build_settlement().confirm().mark_settled().close()
        assert s.status == SettlementStatus.CLOSED

    def test_full_happy_path(self) -> None:
        s = _build_settlement()
        s = s.confirm()
        s = s.mark_settled()
        s = s.close()
        assert s.status == SettlementStatus.CLOSED

    # ---- 取消分支 ----

    def test_draft_to_cancelled(self) -> None:
        s = _build_settlement().cancel()
        assert s.status == SettlementStatus.CANCELLED

    def test_confirmed_to_cancelled(self) -> None:
        s = _build_settlement().confirm().cancel()
        assert s.status == SettlementStatus.CANCELLED

    # ---- 非法转换拒绝 ----

    def test_confirm_from_confirmed_rejected(self) -> None:
        s = _build_settlement().confirm()
        with pytest.raises(FINError) as exc:
            s.confirm()
        assert exc.value.code == FINErrorCode.SETTLEMENT_INVALID_TRANSITION

    def test_mark_settled_from_draft_rejected(self) -> None:
        s = _build_settlement()
        with pytest.raises(FINError) as exc:
            s.mark_settled()
        assert exc.value.code == FINErrorCode.SETTLEMENT_INVALID_TRANSITION

    def test_close_from_confirmed_rejected(self) -> None:
        s = _build_settlement().confirm()
        with pytest.raises(FINError) as exc:
            s.close()
        assert exc.value.code == FINErrorCode.SETTLEMENT_INVALID_TRANSITION

    def test_cancel_from_settled_rejected(self) -> None:
        s = _build_settlement().confirm().mark_settled()
        with pytest.raises(FINError) as exc:
            s.cancel()
        assert exc.value.code == FINErrorCode.SETTLEMENT_INVALID_TRANSITION

    def test_cancel_from_closed_rejected(self) -> None:
        s = _build_settlement().confirm().mark_settled().close()
        with pytest.raises(FINError) as exc:
            s.cancel()
        assert exc.value.code == FINErrorCode.SETTLEMENT_INVALID_TRANSITION

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_settlement()
        confirmed = original.confirm()
        assert original.status == SettlementStatus.DRAFT
        assert confirmed.status == SettlementStatus.CONFIRMED
        assert original is not confirmed