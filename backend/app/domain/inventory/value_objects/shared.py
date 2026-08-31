"""INV 共享值对象与枚举 - 库存事务类型、方向、单据类型、状态等。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class TransactionType(str, Enum):
    PURCHASE_RECEIPT = "purchase_receipt"
    SALES_ISSUE = "sales_issue"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"
    RETURN_IN = "return_in"
    RETURN_OUT = "return_out"
    INSPECT_PASS = "inspect_pass"
    INSPECT_FAIL = "inspect_fail"
    BLOCK = "block"
    UNBLOCK = "unblock"


class Direction(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


_TRANSACTION_DIRECTION_MAP: dict[TransactionType, Direction] = {
    TransactionType.PURCHASE_RECEIPT: Direction.INBOUND,
    TransactionType.TRANSFER_IN: Direction.INBOUND,
    TransactionType.ADJUSTMENT_IN: Direction.INBOUND,
    TransactionType.RETURN_IN: Direction.INBOUND,
    TransactionType.INSPECT_PASS: Direction.INBOUND,
    TransactionType.UNBLOCK: Direction.INBOUND,
    TransactionType.SALES_ISSUE: Direction.OUTBOUND,
    TransactionType.TRANSFER_OUT: Direction.OUTBOUND,
    TransactionType.ADJUSTMENT_OUT: Direction.OUTBOUND,
    TransactionType.RETURN_OUT: Direction.OUTBOUND,
    TransactionType.INSPECT_FAIL: Direction.OUTBOUND,
    TransactionType.BLOCK: Direction.OUTBOUND,
}


def direction_of(tx_type: TransactionType) -> Direction:
    return _TRANSACTION_DIRECTION_MAP[tx_type]


class DocumentType(str, Enum):
    PURCHASE_ORDER = "purchase_order"
    SALES_ORDER = "sales_order"
    RECEIPT = "receipt"
    ISSUE = "issue"
    TRANSFER_ORDER = "transfer_order"
    COUNT_ORDER = "count_order"
    ADJUSTMENT_ORDER = "adjustment_order"


class ReservationStatus(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"
    CONSUMED = "consumed"
    EXPIRED = "expired"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NegativePolicyMode(str, Enum):
    GLOBAL_FORBID = "global_forbid"
    GLOBAL_ALLOW = "global_allow"
    BY_BUSINESS = "by_business"
    BY_WAREHOUSE = "by_warehouse"
    REQUIRE_APPROVAL = "require_approval"


class LocationType(str, Enum):
    STORAGE = "storage"
    PICKING = "picking"
    RECEIVING = "receiving"
    RETURN = "return"
    INSPECTION = "inspection"


class CostModelType(str, Enum):
    MOVING_AVERAGE = "moving_average"
    WEIGHTED_AVERAGE = "weighted_average"
    FIFO = "fifo"
    STANDARD_COST = "standard_cost"
    ACTUAL_COST = "actual_cost"


class CapacityEnforceMode(str, Enum):
    WARN = "warn"
    REJECT = "reject"


class ProductStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class DocumentStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    RECEIVING = "receiving"
    PICKING = "picking"
    IN_TRANSIT = "in_transit"
    EXECUTING = "executing"
    SHIPPED = "shipped"
    RECEIVED = "received"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    COUNTING = "counting"
    COUNTED = "counted"
    DIFF_ANALYZED = "diff_analyzed"


@dataclass(frozen=True)
class Ownership:
    """四级归属值对象 - Tenant/Org/Site/Warehouse。"""

    tenant_id: UUID
    organization_id: UUID | None = None
    site_id: UUID | None = None
    warehouse_id: UUID | None = None

    def validate(self) -> None:
        if self.tenant_id is None:
            raise ValueError("tenant_id is required")

    def belongs_to_tenant(self, tenant_id: UUID) -> bool:
        return self.tenant_id == tenant_id