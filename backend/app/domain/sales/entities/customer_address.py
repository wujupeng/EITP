"""SAL CustomerAddress 实体 - 客户地址，CustomerAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class AddressType(str, Enum):
    SHIPPING = "shipping"
    BILLING = "billing"
    DEFAULT = "default"


@dataclass
class CustomerAddress:
    """客户地址实体。"""

    address_id: UUID = field(default_factory=uuid4)
    customer_id: UUID = field(default_factory=uuid4)
    address_type: AddressType = AddressType.DEFAULT
    province: str = ""
    city: str = ""
    district: str = ""
    detail: str = ""
    consignee: str = ""
    phone: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_shipping(self) -> bool:
        return self.address_type == AddressType.SHIPPING

    @property
    def is_billing(self) -> bool:
        return self.address_type == AddressType.BILLING