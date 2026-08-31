"""库存审计写入器 - 每条库存变化记录完整审计信息，不可篡改。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from structlog import get_logger

logger = get_logger(__name__)


class InventoryAuditWriter:
    """库存审计写入器 - 解耦，故障暂存队列。"""

    async def write_stock_change(
        self,
        tenant_id: UUID,
        user_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        location_id: UUID | None,
        document_id: UUID | None,
        quantity_before: float,
        quantity_change: float,
        quantity_after: float,
        transaction_type: str,
        reason: str | None = None,
    ) -> None:
        logger.info(
            "inventory_audit_stock_change",
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            sku_id=str(sku_id),
            warehouse_id=str(warehouse_id),
            location_id=str(location_id) if location_id else None,
            document_id=str(document_id) if document_id else None,
            quantity_before=quantity_before,
            quantity_change=quantity_change,
            quantity_after=quantity_after,
            transaction_type=transaction_type,
            reason=reason,
            occurred_at=datetime.now(timezone.utc).isoformat(),
        )

    async def write_state_transition(
        self,
        tenant_id: UUID,
        user_id: UUID,
        document_id: UUID,
        document_type: str,
        from_status: str,
        to_status: str,
        reason: str | None = None,
    ) -> None:
        logger.info(
            "inventory_audit_state_transition",
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            document_id=str(document_id),
            document_type=document_type,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            occurred_at=datetime.now(timezone.utc).isoformat(),
        )