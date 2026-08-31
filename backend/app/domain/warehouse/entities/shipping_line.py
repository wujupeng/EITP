"""发货行实体 - ShippingOrderAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class ShippingLine:
    """发货行 - 发货单内的单行明细。"""
    line_id: UUID = field(default_factory=uuid4)
    shipping_order_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    quantity: float = 0.0
    logistics_no: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))