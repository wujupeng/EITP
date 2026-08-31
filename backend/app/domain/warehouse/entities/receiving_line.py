"""收货行实体 - ReceivingOrderAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.warehouse.value_objects.batch_lot import BatchLot


@dataclass
class ReceivingLine:
    """收货行 - 收货单内的单行明细。"""

    line_id: UUID = field(default_factory=uuid4)
    receiving_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    ordered_quantity: float = 0.0
    received_quantity: float = 0.0
    location_id: UUID | None = None
    is_inspection_required: bool = True
    batch_lot: BatchLot = field(default_factory=BatchLot)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def remaining_quantity(self) -> float:
        """未收数量。"""
        return self.ordered_quantity - self.received_quantity

    @property
    def is_fully_received(self) -> bool:
        """是否已全部收货。"""
        return self.received_quantity >= self.ordered_quantity

    @property
    def is_inspection_exempt(self) -> bool:
        """是否免检商品。"""
        return not self.is_inspection_required

    def receive(self, qty: float, location_id: UUID | None = None) -> None:
        """收货 - 累加已收数量。"""
        self.received_quantity += qty
        if location_id is not None:
            self.location_id = location_id