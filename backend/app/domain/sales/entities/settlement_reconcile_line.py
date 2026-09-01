"""SAL SettlementReconcileLine 实体 - 对账明细，SalesSettlementAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class SettlementReconcileLine:
    """对账明细实体 - 发货 vs 订单行对账。"""

    line_id: UUID = field(default_factory=uuid4)
    settlement_id: UUID = field(default_factory=uuid4)
    enterprise_sku_id: UUID = field(default_factory=uuid4)
    order_quantity: float = 0.0
    shipped_quantity: float = 0.0
    unit_price: float = 0.0
    amount: float = 0.0
    diff: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.amount = round(self.shipped_quantity * self.unit_price, 2)
        self.diff = round(self.shipped_quantity - self.order_quantity, 2)

    @property
    def is_consistent(self) -> bool:
        return abs(self.diff) < 0.01