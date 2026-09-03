"""FIN 财务领域事件 - schema 版本 v1。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True)
class FINDomainEvent:
    """FIN 领域事件基类 - 不可变，携带事件 ID、聚合 ID、租户 ID、TraceId、发生时间。"""

    event_id: UUID = field(default_factory=uuid4)
    aggregate_id: str = ""
    tenant_id: UUID | None = None
    trace_id: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: int = 1

    @property
    def event_type(self) -> str:
        return type(self).__name__


@dataclass(frozen=True, kw_only=True)
class SettlementCreatedEvent(FINDomainEvent):
    settlement_no: str = ""
    settlement_type: str = ""
    settlement_amount: str = "0"


@dataclass(frozen=True, kw_only=True)
class SettlementConfirmedEvent(FINDomainEvent):
    settlement_no: str = ""
    ar_voucher_no: str = ""
    ap_voucher_no: str = ""


@dataclass(frozen=True, kw_only=True)
class SettlementSettledEvent(FINDomainEvent):
    settlement_no: str = ""


@dataclass(frozen=True, kw_only=True)
class SettlementCancelledEvent(FINDomainEvent):
    settlement_no: str = ""
    reason: str = ""


@dataclass(frozen=True, kw_only=True)
class PaymentRequestedEvent(FINDomainEvent):
    payment_no: str = ""
    ap_voucher_no: str = ""
    payment_amount: str = "0"


@dataclass(frozen=True, kw_only=True)
class PaymentApprovedEvent(FINDomainEvent):
    payment_no: str = ""
    approver_id: str = ""


@dataclass(frozen=True, kw_only=True)
class PaymentSuccessEvent(FINDomainEvent):
    payment_no: str = ""
    bank_ref: str = ""
    paid_amount: str = "0"


@dataclass(frozen=True, kw_only=True)
class PaymentFailedEvent(FINDomainEvent):
    payment_no: str = ""
    fail_reason: str = ""


@dataclass(frozen=True, kw_only=True)
class ReceiptConfirmedEvent(FINDomainEvent):
    receipt_no: str = ""
    receipt_amount: str = "0"


@dataclass(frozen=True, kw_only=True)
class ReceiptWriteOffEvent(FINDomainEvent):
    receipt_no: str = ""
    ar_voucher_no: str = ""
    write_off_amount: str = "0"


@dataclass(frozen=True, kw_only=True)
class InvoiceIssuedEvent(FINDomainEvent):
    invoice_code: str = ""
    invoice_no: str = ""
    invoice_type: str = ""


@dataclass(frozen=True, kw_only=True)
class InvoiceMatchedEvent(FINDomainEvent):
    invoice_id: str = ""
    business_ref_type: str = ""
    business_ref_id: str = ""


@dataclass(frozen=True, kw_only=True)
class InvoiceVerifiedEvent(FINDomainEvent):
    invoice_id: str = ""


@dataclass(frozen=True, kw_only=True)
class InvoiceArchivedEvent(FINDomainEvent):
    invoice_id: str = ""
    archive_hash: str = ""


@dataclass(frozen=True, kw_only=True)
class InvoiceVoidEvent(FINDomainEvent):
    invoice_id: str = ""
    void_reason: str = ""


@dataclass(frozen=True, kw_only=True)
class ReconBatchCreatedEvent(FINDomainEvent):
    recon_no: str = ""
    period_start: str = ""
    period_end: str = ""


@dataclass(frozen=True, kw_only=True)
class ReconDifferenceHandledEvent(FINDomainEvent):
    diff_id: str = ""
    handle_action: str = ""


@dataclass(frozen=True, kw_only=True)
class ARVoucherGeneratedEvent(FINDomainEvent):
    voucher_no: str = ""
    receivable_amount: str = "0"
    business_ref_type: str = ""
    business_ref_id: str = ""


@dataclass(frozen=True, kw_only=True)
class APVoucherGeneratedEvent(FINDomainEvent):
    voucher_no: str = ""
    payable_amount: str = "0"
    business_ref_type: str = ""
    business_ref_id: str = ""


@dataclass(frozen=True, kw_only=True)
class GLVoucherPostedEvent(FINDomainEvent):
    voucher_no: str = ""
    period: str = ""


@dataclass(frozen=True, kw_only=True)
class GLPeriodClosedEvent(FINDomainEvent):
    period: str = ""


@dataclass(frozen=True, kw_only=True)
class GLRedVoucherCreatedEvent(FINDomainEvent):
    voucher_no: str = ""
    red_original_voucher_no: str = ""


@dataclass(frozen=True, kw_only=True)
class TreasuryTransferExecutedEvent(FINDomainEvent):
    transfer_no: str = ""
    from_account_id: str = ""
    to_account_id: str = ""
    transfer_amount: str = "0"


@dataclass(frozen=True, kw_only=True)
class CollectionTaskGeneratedEvent(FINDomainEvent):
    task_id: str = ""
    ar_voucher_no: str = ""
    overdue_days: int = 0