"""PUR PurchaseReceiptAggregate + AsnAggregate 单元测试 - QC 状态机 + ASN 收货确认。

覆盖 Receipt PENDING→CONFIRMED→QC_IN_PROGRESS→{QC_PASSED→PUTAWAY_COMPLETED, QC_FAILED} 主路径、
各状态前置校验、ASN DRAFT→SENT→CONFIRMED 流转。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.purchasing.aggregates.purchase_receipt_aggregate import (
    AsnAggregate,
    AsnStatus,
    PurchaseReceiptAggregate,
    PurchaseReceiptStatus,
)
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class PurchaseReceiptAggregateTest:
    """PurchaseReceiptAggregate QC 状态机测试。"""

    def test_default_status_is_pending(self) -> None:
        receipt = PurchaseReceiptAggregate()
        assert receipt.status == PurchaseReceiptStatus.PENDING
        assert receipt.wms_receiving_id is None
        assert receipt.confirmed_at is None

    def test_full_qc_passed_lifecycle(self) -> None:
        receipt = PurchaseReceiptAggregate()
        wms_id = uuid4()
        receipt.confirm(wms_id, ["tx-1", "tx-2"])
        assert receipt.status == PurchaseReceiptStatus.CONFIRMED
        assert receipt.wms_receiving_id == wms_id
        assert receipt.inv_transaction_ids == ["tx-1", "tx-2"]
        assert receipt.confirmed_at is not None
        receipt.start_qc()
        assert receipt.status == PurchaseReceiptStatus.QC_IN_PROGRESS
        receipt.pass_qc()
        assert receipt.status == PurchaseReceiptStatus.QC_PASSED
        receipt.complete_putaway()
        assert receipt.status == PurchaseReceiptStatus.PUTAWAY_COMPLETED

    def test_qc_failed_lifecycle(self) -> None:
        receipt = PurchaseReceiptAggregate()
        receipt.confirm(uuid4(), [])
        receipt.start_qc()
        receipt.fail_qc()
        assert receipt.status == PurchaseReceiptStatus.QC_FAILED

    def test_confirm_from_non_pending_rejected(self) -> None:
        receipt = PurchaseReceiptAggregate()
        receipt.confirm(uuid4(), [])
        with pytest.raises(PURError) as exc:
            receipt.confirm(uuid4(), [])
        assert exc.value.code == PURErrorCode.RECEIPT_ORDER_INVALID

    def test_start_qc_from_non_confirmed_rejected(self) -> None:
        receipt = PurchaseReceiptAggregate()
        with pytest.raises(PURError) as exc:
            receipt.start_qc()
        assert exc.value.code == PURErrorCode.RECEIPT_ORDER_INVALID

    def test_pass_qc_from_non_qc_in_progress_rejected(self) -> None:
        receipt = PurchaseReceiptAggregate()
        receipt.confirm(uuid4(), [])
        with pytest.raises(PURError) as exc:
            receipt.pass_qc()
        assert exc.value.code == PURErrorCode.RECEIPT_ORDER_INVALID

    def test_fail_qc_from_non_qc_in_progress_rejected(self) -> None:
        receipt = PurchaseReceiptAggregate()
        receipt.confirm(uuid4(), [])
        with pytest.raises(PURError) as exc:
            receipt.fail_qc()
        assert exc.value.code == PURErrorCode.RECEIPT_ORDER_INVALID

    def test_complete_putaway_from_non_qc_passed_rejected(self) -> None:
        receipt = PurchaseReceiptAggregate()
        receipt.confirm(uuid4(), [])
        receipt.start_qc()
        with pytest.raises(PURError) as exc:
            receipt.complete_putaway()
        assert exc.value.code == PURErrorCode.RECEIPT_ORDER_INVALID


class AsnAggregateTest:
    """AsnAggregate 发送与确认状态机测试。"""

    def test_default_status_is_draft(self) -> None:
        asn = AsnAggregate()
        assert asn.status == AsnStatus.DRAFT
        assert asn.sent_at is None

    def test_send_then_confirm(self) -> None:
        asn = AsnAggregate()
        asn.send()
        assert asn.status == AsnStatus.SENT
        assert asn.sent_at is not None
        asn.confirm()
        assert asn.status == AsnStatus.CONFIRMED

    def test_send_from_non_draft_rejected(self) -> None:
        asn = AsnAggregate()
        asn.send()
        with pytest.raises(PURError) as exc:
            asn.send()
        assert exc.value.code == PURErrorCode.ASN_NOT_FOUND

    def test_confirm_from_non_sent_rejected(self) -> None:
        asn = AsnAggregate()
        with pytest.raises(PURError) as exc:
            asn.confirm()
        assert exc.value.code == PURErrorCode.ASN_NOT_FOUND