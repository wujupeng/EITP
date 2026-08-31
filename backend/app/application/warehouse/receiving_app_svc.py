"""WMS 收货应用服务 - 编排收货执行序列。

序列：权限→DataScope→收货区校验→数量校验→Task→INV PURCHASE_RECEIPT→同步 Position→审计→事件。
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
    WmsReceivingLineORM,
    WmsReceivingOrderORM,
)
from app.infrastructure.warehouse.order_repositories import ReceivingOrderRepository
from app.infrastructure.warehouse.space_repositories import ZoneRepository
from app.infrastructure.warehouse.wms_task_repository import WmsTaskRepository
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class ReceivingAppSvc:
    """收货应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._recv_repo = ReceivingOrderRepository()
        self._task_repo = WmsTaskRepository()
        self._pos_repo = InventoryPositionRepository()
        self._zone_repo = ZoneRepository()
        self._inv_app_svc = InventoryAppSvc(session)

    def _check_auth(self, tenant_id: UUID, permission: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise WMSError(WMSErrorCode.SERVICE_UNAVAILABLE, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise WMSError(WMSErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")

    async def execute_receiving(
        self,
        tenant_id: UUID,
        receiving_id: UUID,
        line_id: UUID,
        received_qty: float,
        location_id: UUID,
        operated_by: UUID,
    ) -> dict:
        """执行收货 - 单行收货。"""
        self._check_auth(tenant_id, "wms:receiving:execute")

        order = await self._recv_repo.get_by_id(self._session, tenant_id, receiving_id)
        if order is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"收货单 {receiving_id} 不存在")

        zone = await self._zone_repo.get_by_id(self._session, tenant_id, order.zone_id)
        if zone is None or zone.zone_function not in ("receiving", "qc"):
            raise WMSError(WMSErrorCode.RECEIVING_ZONE_INVALID, "收货区功能不匹配")

        lines = await self._recv_repo.list_lines(self._session, tenant_id, receiving_id)
        line = next((l for l in lines if l.line_id == line_id), None)
        if line is None:
            raise WMSError(WMSErrorCode.SKU_NOT_FOUND, f"收货行 {line_id} 不存在")

        max_allowed = float(line.ordered_quantity) * (1 + float(order.over_receive_ratio))
        if float(line.received_quantity) + received_qty > max_allowed:
            raise WMSError(WMSErrorCode.RECEIVING_OVER_RECEIVED, "收货数量超出允许范围")

        idempotency_key = f"wms:receiving:{receiving_id}:{line_id}:{received_qty}"
        inv_result = await self._inv_app_svc.execute_transaction(
            tenant_id=tenant_id,
            sku_id=line.sku_id,
            warehouse_id=order.warehouse_id,
            transaction_type="purchase_receipt",
            quantity=received_qty,
            idempotency_key=idempotency_key,
            operated_by=operated_by,
            document_id=receiving_id,
            document_type="wms_receiving",
            location_id=location_id,
        )

        inv_tx_id = inv_result.get("transaction_id")
        new_status = "available" if not line.is_inspection_required else "in_qc"
        existing_pos = await self._pos_repo.query_by_sku_location_status(
            self._session, tenant_id, line.sku_id, location_id, new_status
        )
        if existing_pos is not None:
            existing_pos.quantity = float(existing_pos.quantity) + received_qty
            existing_pos.last_updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            await self._session.flush()
        else:
            pos = WmsInventoryPositionORM(
                tenant_id=tenant_id,
                sku_id=line.sku_id,
                warehouse_id=order.warehouse_id,
                location_id=location_id,
                quantity=received_qty,
                inventory_status=new_status,
            )
            await self._pos_repo.upsert(self._session, pos)

        await self._recv_repo.update_line_received(
            self._session, line, float(line.received_quantity) + received_qty
        )

        audit = WmsOperationAuditORM(
            tenant_id=tenant_id,
            user_id=operated_by,
            event_type="wms_receiving_executed",
            task_id=None,
            sku_id=line.sku_id,
            warehouse_id=order.warehouse_id,
            location_id=location_id,
            before_state={"received_quantity": float(line.received_quantity)},
            after_state={"received_quantity": float(line.received_quantity) + received_qty},
            inv_transaction_ids=[inv_tx_id] if inv_tx_id else [],
            reason=f"收货单 {receiving_id} 行 {line_id} 收货 {received_qty}",
        )
        self._session.add(audit)
        await self._session.flush()

        return {
            "receiving_id": str(receiving_id),
            "line_id": str(line_id),
            "received_qty": received_qty,
            "inv_transaction_id": inv_tx_id,
            "inventory_status": new_status,
        }