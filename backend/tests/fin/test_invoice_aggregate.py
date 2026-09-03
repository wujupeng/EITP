"""InvoiceAggregate 单元测试 - 6 态状态机 + 金额校验 + SHA-256 归档。

覆盖：
- DRAFT→ISSUED→MATCHED→VERIFIED→ARCHIVED 主路径
- VOID 作废分支（含 reason 必填校验）
- 金额不匹配拒绝 (INVOICE_AMOUNT_MISMATCH)
- 归档不可变拒绝 (INVOICE_ARCHIVED_IMMUTABLE / INVOICE_ARCHIVED_VOID_FORBIDDEN)
- 红冲发票缺少原票拒绝 (INVOICE_RED_INVALID)
- 作废原因必填 (INVOICE_VOID_REASON_REQUIRED)
- SHA-256 archive_hash 生成
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.aggregates.invoice_aggregate import (
    InvoiceAggregate,
    InvoiceLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import InvoiceStatus, InvoiceType
from app.domain.fin.value_objects.money import Money


def _line(line_no: int = 1) -> InvoiceLine:
    # 不含税 100 + 税额 13 = 价税合计 113
    return InvoiceLine(
        line_no=line_no,
        product_id="P-001",
        product_name="商品A",
        quantity=Decimal("10"),
        tax_exclusive_amount=Money(Decimal("1000.00")),
        tax_amount=Money(Decimal("130.00")),
        tax_inclusive_amount=Money(Decimal("1130.00")),
    )


def _build_invoice() -> InvoiceAggregate:
    return InvoiceAggregate.create(
        invoice_code="INV-CODE-001",
        invoice_no="INV-001",
        invoice_type=InvoiceType.VAT_NORMAL,
        buyer_info={"name": "买方"},
        seller_info={"name": "卖方"},
        lines=[_line()],
        tenant_id=uuid4(),
    )


class InvoiceAggregateTest:
    """InvoiceAggregate 6 态状态机与金额校验测试。"""

    def test_create_initial_status_is_draft(self) -> None:
        inv = _build_invoice()
        assert inv.status == InvoiceStatus.DRAFT
        assert inv.archive_hash is None

    def test_amount_aggregation(self) -> None:
        inv = _build_invoice()
        assert inv.tax_exclusive_amount.amount == Decimal("1000.00")
        assert inv.tax_amount.amount == Decimal("130.00")
        assert inv.tax_inclusive_amount.amount == Decimal("1130.00")

    # ---- 主路径 ----

    def test_draft_to_issued(self) -> None:
        inv = _build_invoice().issue()
        assert inv.status == InvoiceStatus.ISSUED

    def test_issued_to_matched(self) -> None:
        inv = _build_invoice().issue().match("SETTLEMENT", "ST-001")
        assert inv.status == InvoiceStatus.MATCHED

    def test_matched_to_verified(self) -> None:
        inv = _build_invoice().issue().match("SETTLEMENT", "ST-001").verify()
        assert inv.status == InvoiceStatus.VERIFIED

    def test_verified_to_archived_with_hash(self) -> None:
        inv = _build_invoice().issue().match("SETTLEMENT", "ST-001").verify().archive()
        assert inv.status == InvoiceStatus.ARCHIVED
        assert inv.archive_hash is not None
        assert len(inv.archive_hash) == 64  # SHA-256 hex

    def test_full_happy_path(self) -> None:
        inv = (
            _build_invoice()
            .issue()
            .match("SETTLEMENT", "ST-001")
            .verify()
            .archive()
        )
        assert inv.status == InvoiceStatus.ARCHIVED

    # ---- 作废分支 ----

    def test_void_from_draft(self) -> None:
        inv = _build_invoice().void_invoice("开错")
        assert inv.status == InvoiceStatus.VOID

    def test_void_from_issued(self) -> None:
        inv = _build_invoice().issue().void_invoice("作废")
        assert inv.status == InvoiceStatus.VOID

    def test_void_reason_required(self) -> None:
        with pytest.raises(FINError) as exc:
            _build_invoice().void_invoice("")
        assert exc.value.code == FINErrorCode.INVOICE_VOID_REASON_REQUIRED

    # ---- 金额不匹配拒绝 ----

    def test_amount_mismatch_rejected(self) -> None:
        # 不含税 100 + 税额 13 != 价税合计 200
        bad_line = InvoiceLine(
            line_no=1,
            product_id="P-001",
            product_name="商品A",
            quantity=Decimal("1"),
            tax_exclusive_amount=Money(Decimal("100.00")),
            tax_amount=Money(Decimal("13.00")),
            tax_inclusive_amount=Money(Decimal("200.00")),
        )
        with pytest.raises(FINError) as exc:
            InvoiceAggregate.create(
                invoice_code="BAD",
                invoice_no="INV-BAD",
                invoice_type=InvoiceType.VAT_NORMAL,
                buyer_info={"name": "买方"},
                seller_info={"name": "卖方"},
                lines=[bad_line],
                tenant_id=uuid4(),
            )
        assert exc.value.code == FINErrorCode.INVOICE_AMOUNT_MISMATCH

    def test_empty_lines_rejected(self) -> None:
        with pytest.raises(FINError) as exc:
            InvoiceAggregate.create(
                invoice_code="EMPTY",
                invoice_no="INV-EMPTY",
                invoice_type=InvoiceType.VAT_NORMAL,
                buyer_info={"name": "买方"},
                seller_info={"name": "卖方"},
                lines=[],
                tenant_id=uuid4(),
            )
        assert exc.value.code == FINErrorCode.INVOICE_AMOUNT_MISMATCH

    # ---- 红冲发票校验 ----

    def test_red_invoice_without_original_rejected(self) -> None:
        with pytest.raises(FINError) as exc:
            InvoiceAggregate.create(
                invoice_code="RED",
                invoice_no="INV-RED",
                invoice_type=InvoiceType.RED,
                buyer_info={"name": "买方"},
                seller_info={"name": "卖方"},
                lines=[_line()],
                tenant_id=uuid4(),
            )
        assert exc.value.code == FINErrorCode.INVOICE_RED_INVALID

    def test_red_invoice_with_original_accepted(self) -> None:
        inv = InvoiceAggregate.create(
            invoice_code="RED",
            invoice_no="INV-RED",
            invoice_type=InvoiceType.RED,
            buyer_info={"name": "买方"},
            seller_info={"name": "卖方"},
            lines=[_line()],
            tenant_id=uuid4(),
            red_original_invoice_no="INV-ORIG",
        )
        assert inv.status == InvoiceStatus.DRAFT

    # ---- 归档不可变 ----

    def test_archived_void_forbidden(self) -> None:
        inv = _build_invoice().issue().match("S", "1").verify().archive()
        with pytest.raises(FINError) as exc:
            inv.void_invoice("尝试作废")
        assert exc.value.code == FINErrorCode.INVOICE_ARCHIVED_VOID_FORBIDDEN

    def test_issue_from_issued_rejected_as_archived_immutable(self) -> None:
        # _check_transition 统一抛 INVOICE_ARCHIVED_IMMUTABLE
        inv = _build_invoice().issue()
        with pytest.raises(FINError) as exc:
            inv.issue()
        assert exc.value.code == FINErrorCode.INVOICE_ARCHIVED_IMMUTABLE

    def test_archive_from_draft_rejected(self) -> None:
        inv = _build_invoice()
        with pytest.raises(FINError) as exc:
            inv.archive()
        assert exc.value.code == FINErrorCode.INVOICE_ARCHIVED_IMMUTABLE

    def test_void_twice_rejected(self) -> None:
        inv = _build_invoice().void_invoice("第一次")
        with pytest.raises(FINError) as exc:
            inv.void_invoice("第二次")
        assert exc.value.code == FINErrorCode.INVOICE_ARCHIVED_IMMUTABLE

    # ---- 归档哈希确定性 ----

    def test_archive_hash_deterministic_for_same_content(self) -> None:
        inv1 = _build_invoice().issue().match("S", "1").verify().archive()
        inv2 = _build_invoice().issue().match("S", "1").verify().archive()
        # 相同内容应产生相同哈希
        assert inv1.archive_hash == inv2.archive_hash

    def test_multiple_lines_accumulate(self) -> None:
        inv = InvoiceAggregate.create(
            invoice_code="INV-MULTI",
            invoice_no="INV-MULTI",
            invoice_type=InvoiceType.VAT_NORMAL,
            buyer_info={"name": "买方"},
            seller_info={"name": "卖方"},
            lines=[_line(1), _line(2)],
            tenant_id=uuid4(),
        )
        # 两行各 1000/130/1130 → 合计 2000/260/2260
        assert inv.tax_exclusive_amount.amount == Decimal("2000.00")
        assert inv.tax_amount.amount == Decimal("260.00")
        assert inv.tax_inclusive_amount.amount == Decimal("2260.00")

    def test_immutable_returns_new_instance(self) -> None:
        original = _build_invoice()
        issued = original.issue()
        assert original.status == InvoiceStatus.DRAFT
        assert issued.status == InvoiceStatus.ISSUED
        assert original is not issued