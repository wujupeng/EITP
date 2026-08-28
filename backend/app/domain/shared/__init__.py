"""DDD 共享内核 - 为所有 Bounded Context 提供基类。"""

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.domain_event import DomainEvent
from app.domain.shared.entity import Entity, EntityId
from app.domain.shared.repository import Repository
from app.domain.shared.value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "DomainEvent",
    "Entity",
    "EntityId",
    "Repository",
    "ValueObject",
]