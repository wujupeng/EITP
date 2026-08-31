"""PUR SupplierScope 实体 - 供货范围，SupplierAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class SupplierScopeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class SupplierScope:
    """供货范围实体 - 供应商可供应哪些SKU。"""

    scope_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    supplier_id: UUID = field(default_factory=uuid4)
    enterprise_sku_id: UUID = field(default_factory=uuid4)
    agreement_price: float | None = None
    lead_time_days: int | None = None
    min_order_qty: float | None = None
    min_package_qty: float | None = None
    status: SupplierScopeStatus = SupplierScopeStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def activate(self) -> None:
        self.status = SupplierScopeStatus.ACTIVE

    def deactivate(self) -> None:
        self.status = SupplierScopeStatus.INACTIVE

    @property
    def is_active(self) -> bool:
        return self.status == SupplierScopeStatus.ACTIVE