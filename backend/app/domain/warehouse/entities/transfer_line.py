"""移库行实体 - TransferOrderAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class TransferLine:
    """移库行 - 源库位到目标库位的移动明细。"""

    line_id: UUID = field(default_factory=uuid4)
    transfer_order_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    source_location_id: UUID = field(default_factory=uuid4)
    target_location_id: UUID = field(default_factory=uuid4)
    quantity: float = 0.0
    transferred_quantity: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.transferred_quantity

    @property
    def is_fully_transferred(self) -> bool:
        return self.transferred_quantity >= self.quantity

    def transfer(self, qty: float) -> None:
        self.transferred_quantity += qty