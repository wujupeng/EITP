"""企业商品领域事件 - 企业级（含 tenant_id），复用 MT-001 DomainEventBus 异步发布。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class EnterpriseProductDomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: UUID | None = None
    correlation_id: str | None = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


@dataclass(frozen=True)
class EnterpriseProductReferencedEvent(EnterpriseProductDomainEvent):
    enterprise_product_id: UUID | None = None
    group_product_id: UUID | None = None
    referenced_by: UUID | None = None
    change_type: str = "reference_created"


@dataclass(frozen=True)
class EnterpriseReferenceReleasedEvent(EnterpriseProductDomainEvent):
    enterprise_product_id: UUID | None = None
    group_product_id: UUID | None = None
    released_by: UUID | None = None
    change_type: str = "reference_released"


@dataclass(frozen=True)
class EnterpriseCustomizationPublishedEvent(EnterpriseProductDomainEvent):
    customization_id: UUID | None = None
    enterprise_product_id: UUID | None = None
    version: int = 0
    change_type: str = "customization_published"