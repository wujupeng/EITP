"""WMS 作业审计聚合根 - 承载 WMS 作业审计完整字段，不可变，仅追加。

复用 MT-001 AuditEntry 规范，扩展 WMS 作业特有字段（task_id / sku_id / warehouse_id /
location_id / before_state / after_state / inv_transaction_ids）。
append-only：REVOKE UPDATE/DELETE + Trigger 双保险，保留期 >= 365 天。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.audit.audit_entry import AuditAction


@dataclass(frozen=True)
class WmsOperationAuditAggregate:
    """WMS 作业审计聚合根 - 不可变，仅追加。

    每条记录包含：审计 ID、租户 ID、操作人、事件类型、WMS Task ID、SKU ID、
    仓库 ID、库位 ID、作业前状态、作业后状态、关联 INV Transaction ID 列表、
    变更原因、操作时间、IP 地址。
    """

    audit_id: UUID
    tenant_id: UUID
    user_id: UUID | None
    event_type: AuditAction
    task_id: UUID | None
    sku_id: UUID | None
    warehouse_id: UUID | None
    location_id: UUID | None
    before_state: dict | None
    after_state: dict | None
    inv_transaction_ids: list[UUID]
    reason: str | None
    operated_at: datetime
    ip_address: str | None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        event_type: AuditAction,
        user_id: UUID | None = None,
        task_id: UUID | None = None,
        sku_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        location_id: UUID | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
        inv_transaction_ids: list[UUID] | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> WmsOperationAuditAggregate:
        return cls(
            audit_id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            task_id=task_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            before_state=before_state,
            after_state=after_state,
            inv_transaction_ids=inv_transaction_ids or [],
            reason=reason,
            operated_at=datetime.now(timezone.utc),
            ip_address=ip_address,
        )

    def has_inv_interaction(self) -> bool:
        """是否与 INV Transaction 产生了交互。"""
        return len(self.inv_transaction_ids) > 0

    def is_space_event(self) -> bool:
        """是否为空间变更事件。"""
        return self.event_type == AuditAction.WMS_SPACE_CHANGED

    def is_task_event(self) -> bool:
        """是否为 Task 生命周期事件。"""
        return self.event_type in {
            AuditAction.WMS_TASK_CREATED,
            AuditAction.WMS_TASK_ASSIGNED,
            AuditAction.WMS_TASK_CLAIMED,
            AuditAction.WMS_TASK_COMPLETED,
            AuditAction.WMS_TASK_CANCELLED,
            AuditAction.WMS_TASK_FAILED,
        }

    def is_operation_event(self) -> bool:
        """是否为作业执行事件。"""
        return self.event_type in {
            AuditAction.WMS_RECEIVING_EXECUTED,
            AuditAction.WMS_PUTAWAY_EXECUTED,
            AuditAction.WMS_PICKING_EXECUTED,
            AuditAction.WMS_TRANSFER_EXECUTED,
            AuditAction.WMS_SHIPPING_EXECUTED,
        }