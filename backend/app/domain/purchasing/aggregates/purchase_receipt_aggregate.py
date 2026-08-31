"""PUR 采购到货领域模型 - ASN + PurchaseReceipt 聚合根。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class AsnStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PurchaseReceiptStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    QC_IN_PROGRESS = "qc_in_progress"
    QC_PASSED = "qc_passed"
    QC_FAILED = "qc_failed"
    PUTAWAY_COMPLETED = "putaway_completed"
    CANCELLED = "cancelled"


@dataclass
class AsnLine:
    line_id: UUID = field(default_factory=uuid4)
    order_line_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    expected_quantity: float = 0.0


@dataclass
class AsnAggregate:
    asn_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    asn_code: str = ""
    order_id: UUID = field(default_factory=uuid4)
    supplier_id: UUID = field(default_factory=uuid4)
    warehouse_id: UUID = field(default_factory=uuid4)
    lines: list[AsnLine] = field(default_factory=list)
    status: AsnStatus = AsnStatus.DRAFT
    sent_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def send(self) -> None:
        if self.status != AsnStatus.DRAFT:
            raise PURError(PURErrorCode.ASN_NOT_FOUND, "ASN非草稿状态不可发送")
        self.status = AsnStatus.SENT
        self.sent_at = datetime.now(timezone.utc)

    def confirm(self) -> None:
        if self.status != AsnStatus.SENT:
            raise PURError(PURErrorCode.ASN_NOT_FOUND, "ASN非已发送状态不可确认")
        self.status = AsnStatus.CONFIRMED


@dataclass
class PurchaseReceiptLine:
    line_id: UUID = field(default_factory=uuid4)
    order_line_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    received_quantity: float = 0.0
    qc_result: str = ""
    wms_receiving_id: UUID | None = None


@dataclass
class PurchaseReceiptAggregate:
    receipt_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    receipt_code: str = ""
    order_id: UUID = field(default_factory=uuid4)
    asn_id: UUID | None = None
    supplier_id: UUID = field(default_factory=uuid4)
    warehouse_id: UUID = field(default_factory=uuid4)
    lines: list[PurchaseReceiptLine] = field(default_factory=list)
    status: PurchaseReceiptStatus = PurchaseReceiptStatus.PENDING
    wms_receiving_id: UUID | None = None
    inv_transaction_ids: list[str] = field(default_factory=list)
    confirmed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def confirm(self, wms_receiving_id: UUID, inv_tx_ids: list[str]) -> None:
        if self.status != PurchaseReceiptStatus.PENDING:
            raise PURError(PURErrorCode.RECEIPT_ORDER_INVALID, "收货单非待收状态")
        self.status = PurchaseReceiptStatus.CONFIRMED
        self.wms_receiving_id = wms_receiving_id
        self.inv_transaction_ids = inv_tx_ids
        self.confirmed_at = datetime.now(timezone.utc)

    def start_qc(self) -> None:
        if self.status != PurchaseReceiptStatus.CONFIRMED:
            raise PURError(PURErrorCode.RECEIPT_ORDER_INVALID, "收货单非已确认状态不可质检")
        self.status = PurchaseReceiptStatus.QC_IN_PROGRESS

    def pass_qc(self) -> None:
        if self.status != PurchaseReceiptStatus.QC_IN_PROGRESS:
            raise PURError(PURErrorCode.RECEIPT_ORDER_INVALID, "收货单非质检中状态不可通过")
        self.status = PurchaseReceiptStatus.QC_PASSED

    def fail_qc(self) -> None:
        if self.status != PurchaseReceiptStatus.QC_IN_PROGRESS:
            raise PURError(PURErrorCode.RECEIPT_ORDER_INVALID, "收货单非质检中状态不可失败")
        self.status = PurchaseReceiptStatus.QC_FAILED

    def complete_putaway(self) -> None:
        if self.status != PurchaseReceiptStatus.QC_PASSED:
            raise PURError(PURErrorCode.RECEIPT_ORDER_INVALID, "收货单非质检通过状态不可完成上架")
        self.status = PurchaseReceiptStatus.PUTAWAY_COMPLETED