"""WMS 移库应用服务 - 编排移库执行序列。

序列：权限→同仓库校验→审批→Task→INV TRANSFER_OUT+TRANSFER_IN→同步 Position→审计→事件。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.inv.inv_app_svc import InventoryAppSvc
from app.infrastructure.warehouse.inventory_position_repository import (
    InventoryPositionRepository,
)
from app.infrastructure.warehouse.models import WmsOperationAuditORM
from app.infrastructure.warehouse.order_repositories import TransferOrderRepository
from app.infrastructure.warehouse.space_repositories import LocationRepository
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class TransferAppSvc:
    """移库应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._transfer_repo = TransferOrderRepository()
        self._pos_repo = InventoryPositionRepository()
        self._loc_repo = LocationRepository()
        self._inv_app_svc = InventoryAppSvc(session)

    def _check_auth(self, tenant_id: UUID, permission: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise WMSError(WMSErrorCode.SERVICE_UNAVAILABLE, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise WMSError(WMSErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")

    async def submit_for_approval(
        self, tenant_id: UUID, transfer_id: UUID
    ) -> dict:
        """提交移库审批。"""
        self._check_auth(tenant_id, "wms:transfer:execute")
        order = await self._transfer_repo.get_by_id(self._session, tenant_id, transfer_id)
        if order is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"移库单 {transfer_id} 不存在")
        order.status = "submitted"
        await self._session.flush()
        return {"transfer_id": str(transfer_id), "status": "submitted"}

    async def approve(
        self,
        tenant_id: UUID,
        transfer_id: UUID,
        approver_id: UUID,
        opinion: str = "",
    ) -> dict:
        """审批移库。"""
        self._check_auth(tenant_id, "wms:transfer:approve")
        order = await self._transfer_repo.get_by_id(self._session, tenant_id, transfer_id)
        if order is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"移库单 {transfer_id} 不存在")
        order.status = "approved"
        order.approver_id = approver_id
        order.approved_at = datetime.now(timezone.utc)
        order.approval_opinion = opinion
        await self._session.flush()
        return {"transfer_id": str(transfer_id), "status": "approved"}

    async def execute_transfer(
        self,
        tenant_id: UUID,
        transfer_id: UUID,
        line_id: UUID,
        transfer_qty: float,
        operated_by: UUID,
    ) -> dict:
        """执行移库 - 单行移库。"""
        self._check_auth(tenant_id, "wms:transfer:execute")

        order = await self._transfer_repo.get_by_id(self._session, tenant_id, transfer_id)
        if order is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"移库单 {transfer_id} 不存在")

        if order.require_approval and order.status != "approved":
            raise WMSError(WMSErrorCode.TASK_INVALID_STATE_TRANSITION, "移库单未审批")

        lines = await self._transfer_repo.list_lines(self._session, tenant_id, transfer_id)
        line = next((l for l in lines if l.line_id == line_id), None)
        if line is None:
            raise WMSError(WMSErrorCode.SKU_NOT_FOUND, f"移库行 {line_id} 不存在")

        src_loc = await self._loc_repo.get_by_id(self._session, tenant_id, line.source_location_id)
        tgt_loc = await self._loc_repo.get_by_id(self._session, tenant_id, line.target_location_id)
        if src_loc is not None and tgt_loc is not None:
            if src_loc.warehouse_id != tgt_loc.warehouse_id:
                raise WMSError(WMSErrorCode.TRANSFER_CROSS_WAREHOUSE, "跨仓库移库被拒绝")

        if float(line.transferred_quantity) + transfer_qty > float(line.quantity):
            raise WMSError(WMSErrorCode.PICKING_QTY_MISMATCH, "移库数量超出总量")

        idem_out = f"wms:transfer:{transfer_id}:{line_id}:out:{transfer_qty}"
        idem_in = f"wms:transfer:{transfer_id}:{line_id}:in:{transfer_qty}"

        inv_out = await self._inv_app_svc.execute_transaction(
            tenant_id=tenant_id,
            sku_id=line.sku_id,
            warehouse_id=order.warehouse_id,
            transaction_type="transfer_out",
            quantity=transfer_qty,
            idempotency_key=idem_out,
            operated_by=operated_by,
            location_id=line.source_location_id,
        )
        inv_in = await self._inv_app_svc.execute_transaction(
            tenant_id=tenant_id,
            sku_id=line.sku_id,
            warehouse_id=order.warehouse_id,
            transaction_type="transfer_in",
            quantity=transfer_qty,
            idempotency_key=idem_in,
            operated_by=operated_by,
            location_id=line.target_location_id,
        )

        src_positions = await self._pos_repo.query_by_location(
            self._session, tenant_id, line.source_location_id
        )
        for pos in src_positions:
            if pos.sku_id == line.sku_id and pos.inventory_status == "available":
                pos.quantity = float(pos.quantity) - transfer_qty
                pos.last_updated_at = datetime.now(timezone.utc)
                break

        tgt_positions = await self._pos_repo.query_by_location(
            self._session, tenant_id, line.target_location_id
        )
        existing = next(
            (p for p in tgt_positions if p.sku_id == line.sku_id and p.inventory_status == "available"),
            None,
        )
        if existing is not None:
            existing.quantity = float(existing.quantity) + transfer_qty
            existing.last_updated_at = datetime.now(timezone.utc)
        else:
            from app.infrastructure.warehouse.models import WmsInventoryPositionORM
            new_pos = WmsInventoryPositionORM(
                tenant_id=tenant_id,
                sku_id=line.sku_id,
                warehouse_id=order.warehouse_id,
                location_id=line.target_location_id,
                quantity=transfer_qty,
                inventory_status="available",
            )
            await self._pos_repo.upsert(self._session, new_pos)

        line.transferred_quantity = float(line.transferred_quantity) + transfer_qty
        await self._session.flush()

        audit = WmsOperationAuditORM(
            tenant_id=tenant_id,
            user_id=operated_by,
            event_type="wms_transfer_executed",
            sku_id=line.sku_id,
            warehouse_id=order.warehouse_id,
            location_id=line.target_location_id,
            before_state={"transferred_quantity": float(line.transferred_quantity) - transfer_qty},
            after_state={"transferred_quantity": float(line.transferred_quantity)},
            inv_transaction_ids=[inv_out.get("transaction_id"), inv_in.get("transaction_id")],
            reason=f"移库单 {transfer_id} 行 {line_id} 移库 {transfer_qty}",
        )
        self._session.add(audit)
        await self._session.flush()

        return {
            "transfer_id": str(transfer_id),
            "line_id": str(line_id),
            "transfer_qty": transfer_qty,
            "inv_transaction_ids": [inv_out.get("transaction_id"), inv_in.get("transaction_id")],
        }