"""SAL CustomerContact 实体 - 客户联系人，CustomerAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class CustomerContact:
    """客户联系人实体。"""

    contact_id: UUID = field(default_factory=uuid4)
    customer_id: UUID = field(default_factory=uuid4)
    name: str = ""
    phone: str = ""
    email: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))