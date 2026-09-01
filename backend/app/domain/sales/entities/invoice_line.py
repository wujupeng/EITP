"""SAL InvoiceLine 实体 - 发票行，SalesInvoiceAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class InvoiceLine:
    """发票行实体。"""

    line_id: UUID = field(default_factory=uuid4)
    invoice_id: UUID = field(default_factory=uuid4)
    enterprise_sku_id: UUID = field(default_factory=uuid4)
    quantity: float = 0.0
    unit_price: float = 0.0
    amount: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.amount = round(self.quantity * self.unit_price, 2)