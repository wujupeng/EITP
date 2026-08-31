"""拣货行实体 - PickingTaskAggregate 内部实体，支持多库位拆分。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class PickingLine:
    """拣货行 - 支持多库位拆分（如需 100 但单库位仅 60，拆分为两库位）。"""

    line_id: UUID = field(default_factory=uuid4)
    picking_task_id: UUID = field(default_factory=uuid4)
    sku_id: UUID = field(default_factory=uuid4)
    source_location_id: UUID = field(default_factory=uuid4)
    required_quantity: float = 0.0
    picked_quantity: float = 0.0
    strategy: str = "fifo"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def remaining_quantity(self) -> float:
        return self.required_quantity - self.picked_quantity

    @property
    def is_fully_picked(self) -> bool:
        return self.picked_quantity >= self.required_quantity

    def pick(self, qty: float) -> None:
        """拣货 - 累加已拣数量。"""
        self.picked_quantity += qty