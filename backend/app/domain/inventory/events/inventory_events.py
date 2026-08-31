"""库存领域事件 - 复用 MT-001 DomainEventBus 异步发布。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class InventoryDomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: UUID | None = None
    transaction_id: UUID | None = None
    correlation_id: str | None = None
    document_id: UUID | None = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


@dataclass(frozen=True)
class StockChangedEvent(InventoryDomainEvent):
    sku_id: UUID | None = None
    warehouse_id: UUID | None = None
    location_id: UUID | None = None
    transaction_type: str = ""
    quantity_before: float = 0.0
    quantity_change: float = 0.0
    quantity_after: float = 0.0
    ledger_id: UUID | None = None


@dataclass(frozen=True)
class ReservationCreatedEvent(InventoryDomainEvent):
    reservation_id: UUID | None = None
    sku_id: UUID | None = None
    warehouse_id: UUID | None = None
    reserved_quantity: float = 0.0


@dataclass(frozen=True)
class ReservationReleasedEvent(InventoryDomainEvent):
    reservation_id: UUID | None = None
    sku_id: UUID | None = None
    warehouse_id: UUID | None = None
    released_quantity: float = 0.0
    reason: str = "manual"


@dataclass(frozen=True)
class DocumentStateChangedEvent(InventoryDomainEvent):
    document_type: str = ""
    from_status: str = ""
    to_status: str = ""
    operated_by: UUID | None = None


@dataclass(frozen=True)
class NegativeStockTriggeredEvent(InventoryDomainEvent):
    sku_id: UUID | None = None
    warehouse_id: UUID | None = None
    quantity_after: float = 0.0
    forced_by: UUID | None = None


@dataclass(frozen=True)
class CostModelSwitchedEvent(InventoryDomainEvent):
    old_model: str = ""
    new_model: str = ""
    sku_id: UUID | None = None


@dataclass(frozen=True)
class ProductStatusChangedEvent(InventoryDomainEvent):
    product_id: UUID | None = None
    from_status: str = ""
    to_status: str = ""