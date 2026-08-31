"""WMS 上架应用服务 - 编排上架执行序列。

序列：权限→目标库位校验→Task→INV TRANSFER_OUT+TRANSFER_IN→同步 Position→审计→事件。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inv.inv_app_svc import InventoryAppSvc
from app.infrastructure.warehouse.inventory_position_repository import (
    InventoryPositionRepository,
)
from app.infrastructure.warehouse.models import (
    WmsInventoryPositionORM,
    WmsOperationAuditORM,
)
from app.infrastructure.warehouse.order_repositories import PutawayTaskRepository
from app.infrastructure.warehouse.space_repositories import LocationRepository
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class PutawayAppSvc:
    """上架应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._putaway_repo = PutawayTaskRepository()
        self._pos_repo = InventoryPositionRepository()
        self._loc_repo = LocationRepository()
        self._inv_app_svc = InventoryAppSvc(session)

    def _check_auth(self, tenant_id: UUID, permission: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise WMSError(WMSErrorCode.SERVICE_UNAVAILABLE, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise WMSError(WMSErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")

    async def execute_putaway(
        self,
        tenant_id: UUID,
        putaway_id: UUID,
        target_location_id: UUID,
        putaway_qty: float,
        operated_by: UUID,
    ) -> dict:
        """执行上架 - 从收货区/质检区上架到存储区。"""
        self._check_auth(tenant_id, "wms:putaway:execute")

        task = await self._putaway_repo.get_by_id(self._session, tenant_id, putaway_id)
        if task is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"上架任务 {putaway_id} 不存在")

        target_loc = await self._loc_repo.get_by_id(self._session, tenant_id, target_location_id)
        if target_loc is None:
            raise WMSError(WMSErrorCode.PUTAWAY_LOCATION_DISABLED, "目标库位不存在")
        if target_loc.status != "active":
            raise WMSError(WMSErrorCode.PUTAWAY_LOCATION_DISABLED, "目标库位已停用")

        if float(task.putaway_quantity) + putaway_qty > float(task.quantity):
            raise WMSError(WMSErrorCode.RECEIVING_OVER_RECEIVED, "上架数量超出任务总量")

        idem_out = f"wms:putaway:{putaway_id}:out:{putaway_qty}"
        idem_in = f"wms:putaway:{putaway_id}:in:{putaway_qty}"

        inv_out = await self._inv_app_svc.execute_transaction(
            tenant_id=tenant_id,
            sku_id=task.sku_id,
            warehouse_id=target_loc.warehouse_id,
            transaction_type="transfer_out",
            quantity=putaway_qty,
            idempotency_key=idem_out,
            operated_by=operated_by,
            location_id=task.source_location_id,
        )
        inv_in = await self._inv_app_svc.execute_transaction(
            tenant_id=tenant_id,
            sku_id=task.sku_id,
            warehouse_id=target_loc.warehouse_id,
            transaction_type="transfer_in",
            quantity=putaway_qty,
            idempotency_key=idem_in,
            operated_by=operated_by,
            location_id=target_location_id,
        )

        src_positions = await self._pos_repo.query_by_location(
            self._session, tenant_id, task.source_location_id
        )
        for pos in src_positions:
            if pos.sku_id == task.sku_id and pos.inventory_status in ("available", "in_qc"):
                pos.quantity = float(pos.quantity) - putaway_qty
                pos.last_updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                break

        existing_pos = await self._pos_repo.query_by_sku_location_status(
            self._session, tenant_id, task.sku_id, target_location_id, "available"
        )
        if existing_pos is not None:
            existing_pos.quantity = float(existing_pos.quantity) + putaway_qty
            existing_pos.last_updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        else:
            new_pos = WmsInventoryPositionORM(
                tenant_id=tenant_id,
                sku_id=task.sku_id,
                warehouse_id=target_loc.warehouse_id,
                location_id=target_location_id,
                quantity=putaway_qty,
                inventory_status="available",
            )
            await self._pos_repo.upsert(self._session, new_pos)

        task.putaway_quantity = float(task.putaway_quantity) + putaway_qty
        if float(task.putaway_quantity) >= float(task.quantity):
            task.status = "completed"
            task.completed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        task.target_location_id = target_location_id
        await self._session.flush()

        audit = WmsOperationAuditORM(
            tenant_id=tenant_id,
            user_id=operated_by,
            event_type="wms_putaway_executed",
            sku_id=task.sku_id,
            warehouse_id=target_loc.warehouse_id,
            location_id=target_location_id,
            before_state={"putaway_quantity": float(task.putaway_quantity) - putaway_qty},
            after_state={"putaway_quantity": float(task.putaway_quantity)},
            inv_transaction_ids=[inv_out.get("transaction_id"), inv_in.get("transaction_id")],
            reason=f"上架任务 {putaway_id} 上架 {putaway_qty} 到 {target_location_id}",
        )
        self._session.add(audit)
        await self._session.flush()

        return {
            "putaway_id": str(putaway_id),
            "putaway_qty": putaway_qty,
            "target_location_id": str(target_location_id),
            "inv_transaction_ids": [inv_out.get("transaction_id"), inv_in.get("transaction_id")],
        }