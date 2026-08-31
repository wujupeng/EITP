"""PUR QuotationLine 实体 - 报价行。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class QuotationLine:
    """报价行实体 - QuotationAggregate 内部实体。"""

    line_id: UUID = field(default_factory=uuid4)
    quotation_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    unit_price: float = 0.0
    lead_time_days: int = 0
    min_order_qty: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))