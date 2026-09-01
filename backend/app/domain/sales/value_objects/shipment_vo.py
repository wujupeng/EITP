"""SAL 发货与包装值对象 - ShipmentStatus/PickingStrategy/PackingStatus。"""

from __future__ import annotations

from enum import Enum


class ShipmentStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PICKING = "picking"
    PACKED = "packed"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PickingStrategy(str, Enum):
    FIFO = "fifo"
    FEFO = "fefo"
    BY_BATCH = "by_batch"
    BY_LOCATION = "by_location"


class PackingStatus(str, Enum):
    DRAFT = "draft"
    PACKED = "packed"
    CANCELLED = "cancelled"