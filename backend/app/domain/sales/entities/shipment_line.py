"""SAL ShipmentLine 实体 - 发货行，ShipmentOrderAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import SALError, SALErrorCode


@dataclass
class ShipmentLine:
    """发货行实体 - 发货数量校验（不超订单未发量，由 PartialFulfillmentService 校验）。"""

    line_id: UUID = field(default_factory=uuid4)
    shipment_id: UUID = field(default_factory=uuid4)
    order_line_id: UUID = field(default_factory=uuid4)
    enterprise_sku_id: UUID = field(default_factory=uuid4)
    ship_quantity: float = 0.0
    picking_location: str | None = None
    lot_number: str | None = None
    batch_number: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.ship_quantity <= 0:
            raise SALError(SALErrorCode.SHIPMENT_OVER_SHIPPED, "发货数量必须为正数")