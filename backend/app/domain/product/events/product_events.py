"""商品领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ProductCreatedEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: UUID | None = None
    product_id: UUID | None = None
    product_code: str = ""
    product_name: str = ""

    @property
    def event_type(self) -> str:
        return "ProductCreatedEvent"


@dataclass(frozen=True)
class ProductDisabledEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: UUID | None = None
    product_id: UUID | None = None
    product_code: str = ""

    @property
    def event_type(self) -> str:
        return "ProductDisabledEvent"


@dataclass(frozen=True)
class SkuCreatedEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: UUID | None = None
    product_id: UUID | None = None
    sku_id: UUID | None = None
    sku_code: str = ""

    @property
    def event_type(self) -> str:
        return "SkuCreatedEvent"