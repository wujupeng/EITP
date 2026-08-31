"""集团商品目录领域事件 - 复用 MT-001 DomainEventBus 异步发布。

集团级事件 tenant_id 为 None，含 group_product_id/version/change_type/correlation_id
用于链路追踪与下游缓存更新。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class GroupCatalogDomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: UUID | None = None
    correlation_id: str | None = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


@dataclass(frozen=True)
class GroupProductPublishedEvent(GroupCatalogDomainEvent):
    group_product_id: UUID | None = None
    group_product_code: str = ""
    from_version: int = 0
    to_version: int = 0
    change_type: str = "publish"


@dataclass(frozen=True)
class GroupProductDisabledEvent(GroupCatalogDomainEvent):
    group_product_id: UUID | None = None
    group_product_code: str = ""
    change_type: str = "disable"


@dataclass(frozen=True)
class GroupSkuCreatedEvent(GroupCatalogDomainEvent):
    group_product_id: UUID | None = None
    group_sku_id: UUID | None = None
    group_sku_code: str = ""
    change_type: str = "sku_created"


@dataclass(frozen=True)
class GroupCategoryPublishedEvent(GroupCatalogDomainEvent):
    group_category_id: UUID | None = None
    group_category_code: str = ""
    from_version: int = 0
    to_version: int = 0
    change_type: str = "category_publish"


@dataclass(frozen=True)
class SpecTemplatePublishedEvent(GroupCatalogDomainEvent):
    template_id: UUID | None = None
    template_code: str = ""
    template_level: str = "group"
    change_type: str = "spec_template_published"


@dataclass(frozen=True)
class AttributeTemplatePublishedEvent(GroupCatalogDomainEvent):
    template_id: UUID | None = None
    template_code: str = ""
    template_level: str = "group"
    attribute_name: str = ""
    change_type: str = "attribute_template_published"