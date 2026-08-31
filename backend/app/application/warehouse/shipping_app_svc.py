"""WMS 发货应用服务 - 编排发货执行序列。

序列：权限→拣货已完成校验→发货区校验→录入物流单号→确认发货→审计→事件。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.warehouse.models import WmsOperationAuditORM
from app.infrastructure.warehouse.order_repositories import ShippingOrderRepository
from app.infrastructure.warehouse.space_repositories import ZoneRepository
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class ShippingAppSvc:
    """发货应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._shipping_repo = ShippingOrderRepository()
        self._zone_repo = ZoneRepository()

    def _check_auth(self, tenant_id: UUID, permission: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise WMSError(WMSErrorCode.SERVICE_UNAVAILABLE, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise WMSError(WMSErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")

    async def record_logistics(
        self,
        tenant_id: UUID,
        shipping_id: UUID,
        logistics_no: str,
        logistics_company: str,
        operated_by: UUID,
    ) -> dict:
        """录入物流单号。"""
        self._check_auth(tenant_id, "wms:shipping:execute")

        order = await self._shipping_repo.get_by_id(self._session, tenant_id, shipping_id)
        if order is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"发货单 {shipping_id} 不存在")

        zone = await self._zone_repo.get_by_id(self._session, tenant_id, order.zone_id)
        if zone is None or zone.zone_function != "shipping":
            raise WMSError(WMSErrorCode.SHIPPING_ZONE_INVALID, "发货区功能不匹配")

        if not order.picking_completed:
            raise WMSError(WMSErrorCode.SHIPPING_PICKING_NOT_COMPLETED, "拣货未完成")

        order.logistics_no = logistics_no
        order.logistics_company = logistics_company
        order.status = "executing"
        await self._session.flush()

        audit = WmsOperationAuditORM(
            tenant_id=tenant_id,
            user_id=operated_by,
            event_type="wms_shipping_executed",
            warehouse_id=order.warehouse_id,
            before_state={"status": "draft"},
            after_state={"status": "executing", "logistics_no": logistics_no},
            reason=f"发货单 {shipping_id} 录入物流单号 {logistics_no}",
        )
        self._session.add(audit)
        await self._session.flush()

        return {"shipping_id": str(shipping_id), "logistics_no": logistics_no, "status": "executing"}

    async def confirm_shipping(
        self,
        tenant_id: UUID,
        shipping_id: UUID,
        operated_by: UUID,
    ) -> dict:
        """确认发货完成。"""
        self._check_auth(tenant_id, "wms:shipping:execute")

        order = await self._shipping_repo.get_by_id(self._session, tenant_id, shipping_id)
        if order is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"发货单 {shipping_id} 不存在")
        if order.status != "executing":
            raise WMSError(WMSErrorCode.TASK_INVALID_STATE_TRANSITION, "发货单状态不允许确认")

        order.status = "completed"
        order.shipped_at = datetime.now(timezone.utc)
        await self._session.flush()

        audit = WmsOperationAuditORM(
            tenant_id=tenant_id,
            user_id=operated_by,
            event_type="wms_shipping_executed",
            warehouse_id=order.warehouse_id,
            before_state={"status": "executing"},
            after_state={"status": "completed", "shipped_at": order.shipped_at.isoformat()},
            reason=f"发货单 {shipping_id} 确认发货完成",
        )
        self._session.add(audit)
        await self._session.flush()

        return {"shipping_id": str(shipping_id), "status": "completed"}