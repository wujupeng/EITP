"""PUR 供应商领域事件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SupplierPublishedEvent:
    """供应商发布生效事件。"""

    supplier_id: UUID
    tenant_id: UUID
    supplier_code: str
    status: str = "active"
    event_id: UUID = field(default_factory=uuid4)
    correlation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SupplierDisabledEvent:
    """供应商停用事件。"""

    supplier_id: UUID
    tenant_id: UUID
    supplier_code: str
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))