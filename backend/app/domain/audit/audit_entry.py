"""租户级审计日志 - 不可篡改，仅追加。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class AuditAction(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    LOGIN = "login"
    LOGOUT = "logout"
    CONFIG_CHANGE = "config_change"
    DATASCOPE_VIOLATION = "datascope_violation"
    GROUP_READONLY_VIOLATION = "group_readonly_violation"
    MASTER_PROPAGATE = "master_propagate"
    STOCK_CHANGE = "stock_change"
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_RELEASED = "reservation_released"
    STATE_TRANSITION = "state_transition"
    NEGATIVE_STOCK_FORCED = "negative_stock_forced"
    ADJUSTMENT_EXECUTED = "adjustment_executed"
    BLOCK_EXECUTED = "block_executed"
    UNBLOCK_EXECUTED = "unblock_executed"
    COUNT_DIFF_PROCESSED = "count_diff_processed"
    COST_MODEL_SWITCHED = "cost_model_switched"
    MASTER_DATA_PUBLISHED = "master_data_published"
    MASTER_DATA_VERSION_ROLLBACK = "master_data_version_rollback"
    GOVERNANCE_REQUEST_SUBMITTED = "governance_request_submitted"
    GOVERNANCE_REQUEST_APPROVED = "governance_request_approved"
    GOVERNANCE_REQUEST_REJECTED = "governance_request_rejected"
    GOVERNANCE_REQUEST_PUBLISHED = "governance_request_published"
    GOVERNANCE_REQUEST_ROLLBACK = "governance_request_rollback"
    ENTERPRISE_PRODUCT_REFERENCED = "enterprise_product_referenced"
    ENTERPRISE_REFERENCE_RELEASED = "enterprise_reference_released"
    NEGATIVE_POLICY_CHANGED = "negative_policy_changed"
    GROUP_CATALOG_PUBLISHED = "group_catalog_published"
    ENTERPRISE_CUSTOMIZATION_PUBLISHED = "enterprise_customization_published"
    WMS_SPACE_CHANGED = "wms_space_changed"
    WMS_TASK_CREATED = "wms_task_created"
    WMS_TASK_ASSIGNED = "wms_task_assigned"
    WMS_TASK_CLAIMED = "wms_task_claimed"
    WMS_TASK_COMPLETED = "wms_task_completed"
    WMS_TASK_CANCELLED = "wms_task_cancelled"
    WMS_TASK_FAILED = "wms_task_failed"
    WMS_RECEIVING_EXECUTED = "wms_receiving_executed"
    WMS_PUTAWAY_EXECUTED = "wms_putaway_executed"
    WMS_PICKING_EXECUTED = "wms_picking_executed"
    WMS_TRANSFER_EXECUTED = "wms_transfer_executed"
    WMS_SHIPPING_EXECUTED = "wms_shipping_executed"
    WMS_POSITION_SYNCED = "wms_position_synced"
    WMS_RECONCILE_DIFF_FOUND = "wms_reconcile_diff_found"


@dataclass(frozen=True)
class AuditEntry:
    """审计日志条目 - 不可篡改。

    每条记录包含：租户、操作人、动作、目标实体、前后值、时间戳。
    """

    id: UUID
    tenant_id: UUID
    user_id: UUID | None
    action: AuditAction
    entity_type: str
    entity_id: str
    old_value: dict | None
    new_value: dict | None
    ip_address: str | None
    occurred_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        user_id: UUID | None,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        old_value: dict | None = None,
        new_value: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            occurred_at=datetime.now(timezone.utc),
        )