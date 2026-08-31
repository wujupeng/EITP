"""PUR 采购审计聚合根 - append-only 不可变。

复用 MT-001 AuditEntry 规范，保留期 >= 365 天。
REVOKE UPDATE/DELETE + Trigger 双保险。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class PurchaseAuditAction(str, Enum):
    SUPPLIER_PUBLISHED = "supplier_published"
    SUPPLIER_UPDATED = "supplier_updated"
    SUPPLIER_DISABLED = "supplier_disabled"
    QUOTATION_CREATED = "quotation_created"
    EVALUATION_COMPLETED = "evaluation_completed"
    PURCHASE_REQUEST_CREATED = "purchase_request_created"
    PURCHASE_REQUEST_APPROVED = "purchase_request_approved"
    PURCHASE_REQUEST_REJECTED = "purchase_request_rejected"
    PURCHASE_ORDER_CREATED = "purchase_order_created"
    PURCHASE_ORDER_APPROVED = "purchase_order_approved"
    PURCHASE_ORDER_SENT = "purchase_order_sent"
    PURCHASE_ORDER_CHANGED = "purchase_order_changed"
    PURCHASE_ORDER_CANCELLED = "purchase_order_cancelled"
    PURCHASE_ORDER_CLOSED = "purchase_order_closed"
    ASN_CREATED = "asn_created"
    PURCHASE_RECEIPT_CONFIRMED = "purchase_receipt_confirmed"
    PURCHASE_RECEIPT_QC_COMPLETED = "purchase_receipt_qc_completed"
    PURCHASE_RETURN_CREATED = "purchase_return_created"
    PURCHASE_RETURN_APPROVED = "purchase_return_approved"
    PURCHASE_RETURN_SHIPPED = "purchase_return_shipped"
    PURCHASE_RETURN_COMPLETED = "purchase_return_completed"
    SETTLEMENT_RECONCILED = "settlement_reconciled"
    INVOICE_MATCHED = "invoice_matched"
    PAYMENT_REQUESTED = "payment_requested"
    PAYMENT_COMPLETED = "payment_completed"
    PUR_WMS_INV_INCONSISTENT = "pur_wms_inv_inconsistent"


@dataclass(frozen=True)
class PurchaseAuditAggregate:
    """采购审计聚合根 - 不可变，append-only。"""

    audit_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    event_type: PurchaseAuditAction = PurchaseAuditAction.PURCHASE_ORDER_CREATED
    supplier_id: UUID | None = None
    order_id: UUID | None = None
    receipt_id: UUID | None = None
    return_id: UUID | None = None
    settlement_id: UUID | None = None
    before_state: dict = field(default_factory=dict)
    after_state: dict = field(default_factory=dict)
    wms_receiving_id: UUID | None = None
    inv_transaction_ids: list[str] = field(default_factory=list)
    reason: str = ""
    operated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))