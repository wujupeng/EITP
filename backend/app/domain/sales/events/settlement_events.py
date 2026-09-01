"""SAL 结算领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SalesSettlementReconciledEvent:
    """销售结算对账完成事件。"""

    settlement_id: UUID
    tenant_id: UUID
    order_id: UUID
    receivable_amount: float
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SalesInvoiceMatchedEvent:
    """销售发票匹配完成事件。"""

    invoice_id: UUID
    tenant_id: UUID
    settlement_id: UUID
    invoice_amount: float
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class PaymentReceivedEvent:
    """收款完成事件。"""

    payment_receipt_id: UUID
    tenant_id: UUID
    settlement_id: UUID
    payment_no: str
    payment_amount: float
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))