"""PUR 采购退货 + 采购结算 + 发票 + 付款 聚合根。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class PurchaseReturnStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SettlementStatus(str, Enum):
    PENDING = "pending"
    RECONCILED = "reconciled"
    DIFF_FOUND = "diff_found"
    RESOLVED = "resolved"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    MATCHED = "matched"
    MISMATCHED = "mismatched"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PurchaseReturnLine:
    line_id: UUID = field(default_factory=uuid4)
    order_line_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    return_quantity: float = 0.0
    reason: str = ""


@dataclass
class PurchaseReturnAggregate:
    return_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    return_code: str = ""
    order_id: UUID = field(default_factory=uuid4)
    supplier_id: UUID = field(default_factory=uuid4)
    warehouse_id: UUID | None = None
    lines: list[PurchaseReturnLine] = field(default_factory=list)
    status: PurchaseReturnStatus = PurchaseReturnStatus.DRAFT
    approved_by: UUID | None = None
    inv_transaction_ids: list[str] = field(default_factory=list)
    shipped_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def submit(self) -> None:
        if not self.lines:
            raise PURError(PURErrorCode.RETURN_NOT_FOUND, "退货无明细行")
        self.status = PurchaseReturnStatus.SUBMITTED

    def approve(self, approver_id: UUID) -> None:
        if self.status != PurchaseReturnStatus.SUBMITTED:
            raise PURError(PURErrorCode.RETURN_NOT_APPROVED, "退货非已提交状态不可审批")
        self.status = PurchaseReturnStatus.APPROVED
        self.approved_by = approver_id

    def ship(self, inv_tx_ids: list[str]) -> None:
        if self.status != PurchaseReturnStatus.APPROVED:
            raise PURError(PURErrorCode.RETURN_NOT_APPROVED, "退货非已审批状态不可出库")
        self.status = PurchaseReturnStatus.SHIPPED
        self.inv_transaction_ids = inv_tx_ids
        self.shipped_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        if self.status != PurchaseReturnStatus.SHIPPED:
            raise PURError(PURErrorCode.RETURN_NOT_FOUND, "退货非已出库状态不可完成")
        self.status = PurchaseReturnStatus.COMPLETED


@dataclass
class PurchaseSettlementAggregate:
    settlement_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    settlement_code: str = ""
    order_id: UUID = field(default_factory=uuid4)
    supplier_id: UUID = field(default_factory=uuid4)
    total_amount: float = 0.0
    received_amount: float = 0.0
    diff_amount: float = 0.0
    status: SettlementStatus = SettlementStatus.PENDING
    inv_transaction_ids: list[str] = field(default_factory=list)
    reconciled_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def reconcile(self, received_amount: float) -> None:
        self.received_amount = received_amount
        self.diff_amount = round(self.total_amount - received_amount, 2)
        if abs(self.diff_amount) < 0.01:
            self.status = SettlementStatus.RECONCILED
        else:
            self.status = SettlementStatus.DIFF_FOUND
        self.reconciled_at = datetime.now(timezone.utc)

    def resolve(self) -> None:
        self.status = SettlementStatus.RESOLVED


@dataclass
class InvoiceAggregate:
    invoice_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    invoice_code: str = ""
    supplier_id: UUID = field(default_factory=uuid4)
    settlement_id: UUID | None = None
    invoice_amount: float = 0.0
    matched_amount: float = 0.0
    status: InvoiceStatus = InvoiceStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def match(self, expected_amount: float) -> None:
        self.matched_amount = expected_amount
        if abs(self.invoice_amount - expected_amount) < 0.01:
            self.status = InvoiceStatus.MATCHED
        else:
            self.status = InvoiceStatus.MISMATCHED


@dataclass
class PaymentRequestAggregate:
    payment_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    payment_code: str = ""
    settlement_id: UUID = field(default_factory=uuid4)
    supplier_id: UUID = field(default_factory=uuid4)
    amount: float = 0.0
    status: PaymentStatus = PaymentStatus.PENDING
    inv_transaction_ids: list[str] = field(default_factory=list)
    paid_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def approve(self) -> None:
        if self.status != PaymentStatus.PENDING:
            raise PURError(PURErrorCode.PAYMENT_ALREADY_COMPLETED, "付款非待付状态不可审批")
        self.status = PaymentStatus.APPROVED

    def execute(self, inv_tx_ids: list[str]) -> None:
        if self.status != PaymentStatus.APPROVED:
            raise PURError(PURErrorCode.PAYMENT_NOT_FOUND, "付款非已审批状态不可执行")
        self.status = PaymentStatus.EXECUTING
        self.inv_transaction_ids = inv_tx_ids

    def complete(self) -> None:
        if self.status != PaymentStatus.EXECUTING:
            raise PURError(PURErrorCode.PAYMENT_NOT_FOUND, "付款非执行中状态不可完成")
        self.status = PaymentStatus.COMPLETED
        self.paid_at = datetime.now(timezone.utc)

    def fail(self) -> None:
        self.status = PaymentStatus.FAILED