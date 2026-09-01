"""SAL PackingLine 实体 - 装箱明细，PackingRecordAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class PackingLine:
    """装箱明细实体。"""

    line_id: UUID = field(default_factory=uuid4)
    packing_id: UUID = field(default_factory=uuid4)
    enterprise_sku_id: UUID = field(default_factory=uuid4)
    quantity: float = 0.0
    carton_no: str = ""
    gross_weight: float = 0.0
    net_weight: float = 0.0
    volume: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))