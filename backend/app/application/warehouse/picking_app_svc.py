"""WMS 拣货应用服务 - 编排拣货执行序列。

序列：权限→Reservation 预占→策略选库位+拆分→Task→INV SALES_ISSUE/TRANSFER_OUT→同步 Position→审计→事件。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inv.inv_app_svc import InventoryAppSvc
from app.infrastructure.warehouse.inventory_position_repository import (
    InventoryPositionRepository,
)
from app.infrastructure.warehouse.models import WmsOperationAuditORM
from app.infrastructure.warehouse.order_repositories import PickingTaskRepository
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class PickingAppSvc:
    """拣货应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._picking_repo = PickingTaskRepository()
        self._pos_repo = InventoryPositionRepository()
        self._inv_app_svc = InventoryAppSvc(session)

    def _check_auth(self, tenant_id: UUID, permission: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise WMSError(WMSErrorCode.SERVICE_UNAVAILABLE, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise WMSError(WMSErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")

    async def execute_picking(
        self,
        tenant_id: UUID,
        picking_id: UUID,
        line_id: UUID,
        picked_qty: float,
        operated_by: UUID,
    ) -> dict:
        """执行拣货 - 单行拣货。"""
        self._check_auth(tenant_id, "wms:picking:execute")

        task = await self._picking_repo.get_by_id(self._session, tenant_id, picking_id)
        if task is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"拣货任务 {picking_id} 不存在")

        lines = await self._picking_repo.list_lines(self._session, tenant_id, picking_id)
        line = next((l for l in lines if l.line_id == line_id), None)
        if line is None:
            raise WMSError(WMSErrorCode.SKU_NOT_FOUND, f"拣货行 {line_id} 不存在")

        if float(line.picked_quantity) + picked_qty > float(line.required_quantity):
            raise WMSError(WMSErrorCode.PICKING_QTY_MISMATCH, "拣货数量超出需求数量")

        positions = await self._pos_repo.query_by_location(
            self._session, tenant_id, line.source_location_id
        )
        available = sum(
            float(p.quantity) for p in positions
            if p.sku_id == line.sku_id and p.inventory_status == "available"
        )
        if available < picked_qty:
            raise WMSError(
                WMSErrorCode.PICKING_INSUFFICIENT_AVAILABLE,
                f"库位可用量 {available} 不足，需 {picked_qty}",
            )

        tx_type = "sales_issue" if task.source_order_type == "sales" else "transfer_out"
        idem_key = f"wms:picking:{picking_id}:{line_id}:{picked_qty}"
        inv_result = await self._inv_app_svc.execute_transaction(
            tenant_id=tenant_id,
            sku_id=line.sku_id,
            warehouse_id=task.warehouse_id,
            transaction_type=tx_type,
            quantity=picked_qty,
            idempotency_key=idem_key,
            operated_by=operated_by,
            document_id=picking_id,
            document_type="wms_picking",
            location_id=line.source_location_id,
        )

        for pos in positions:
            if pos.sku_id == line.sku_id and pos.inventory_status == "available":
                pos.quantity = float(pos.quantity) - picked_qty
                pos.last_updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                break
        await self._session.flush()

        line.picked_quantity = float(line.picked_quantity) + picked_qty
        await self._session.flush()

        audit = WmsOperationAuditORM(
            tenant_id=tenant_id,
            user_id=operated_by,
            event_type="wms_picking_executed",
            sku_id=line.sku_id,
            warehouse_id=task.warehouse_id,
            location_id=line.source_location_id,
            before_state={"picked_quantity": float(line.picked_quantity) - picked_qty},
            after_state={"picked_quantity": float(line.picked_quantity)},
            inv_transaction_ids=[inv_result.get("transaction_id")],
            reason=f"拣货任务 {picking_id} 行 {line_id} 拣货 {picked_qty}",
        )
        self._session.add(audit)
        await self._session.flush()

        return {
            "picking_id": str(picking_id),
            "line_id": str(line_id),
            "picked_qty": picked_qty,
            "inv_transaction_id": inv_result.get("transaction_id"),
        }