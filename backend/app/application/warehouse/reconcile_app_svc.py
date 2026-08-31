"""WMS 对账应用服务 - 编排 WMS↔INV 对账。

序列：权限→聚合 WMS Position→对比 INV Balance→记录差异→发布事件→（可选）修复。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.warehouse.services.reconcile_service import ReconcileService
from app.infrastructure.warehouse.audit_repositories import ReconcileDiffRepository
from app.infrastructure.warehouse.inventory_position_repository import (
    InventoryPositionRepository,
)
from app.infrastructure.warehouse.models import WmsReconcileDiffORM
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class ReconcileAppSvc:
    """对账应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._pos_repo = InventoryPositionRepository()
        self._diff_repo = ReconcileDiffRepository()
        self._reconcile_svc = ReconcileService()

    def _check_auth(self, tenant_id: UUID, permission: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise WMSError(WMSErrorCode.SERVICE_UNAVAILABLE, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise WMSError(WMSErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")

    async def run_reconcile(
        self,
        tenant_id: UUID,
        warehouse_id: UUID,
        inv_balance_provider,
    ) -> list[dict]:
        """执行对账 - 对比 WMS Position 与 INV Balance。

        Args:
            inv_balance_provider: 可调用对象，接收 (tenant_id, sku_id, warehouse_id)，
                                 返回 INV 侧各状态量 dict。
        """
        self._check_auth(tenant_id, "wms:reconcile:execute")

        from app.infrastructure.warehouse.space_repositories import LocationRepository
        loc_repo = LocationRepository()
        locations = await loc_repo.list_available_for_picking(
            self._session, tenant_id, warehouse_id
        )

        checked_skus: set[UUID] = set()
        diffs: list[dict] = []

        for loc in locations:
            positions = await self._pos_repo.query_by_location(
                self._session, tenant_id, loc.location_id
            )
            for pos in positions:
                if pos.sku_id in checked_skus:
                    continue
                checked_skus.add(pos.sku_id)

                wms_agg = await self._pos_repo.aggregate_by_sku_warehouse(
                    self._session, tenant_id, pos.sku_id, warehouse_id
                )
                wms_map = {status: qty for status, qty in wms_agg}

                inv_map = inv_balance_provider(tenant_id, pos.sku_id, warehouse_id)

                all_statuses = set(wms_map.keys()) | set(inv_map.keys())
                for status in all_statuses:
                    wms_qty = wms_map.get(status, 0.0)
                    inv_qty = inv_map.get(status, 0.0)
                    diff_qty = wms_qty - inv_qty
                    if abs(diff_qty) < 1e-9:
                        continue

                    diff_type = self._reconcile_svc.classify_diff(wms_qty, inv_qty)
                    diff_orm = WmsReconcileDiffORM(
                        tenant_id=tenant_id,
                        sku_id=pos.sku_id,
                        warehouse_id=warehouse_id,
                        location_id=None,
                        wms_quantity=wms_qty,
                        inv_quantity=inv_qty,
                        diff_quantity=diff_qty,
                        diff_type=diff_type,
                        status="open",
                    )
                    await self._diff_repo.save(self._session, diff_orm)
                    diffs.append({
                        "diff_id": str(diff_orm.diff_id),
                        "sku_id": str(pos.sku_id),
                        "warehouse_id": str(warehouse_id),
                        "inventory_status": status,
                        "wms_quantity": wms_qty,
                        "inv_quantity": inv_qty,
                        "diff_quantity": diff_qty,
                        "diff_type": diff_type,
                    })

        return diffs

    async def list_open_diffs(self, tenant_id: UUID) -> list[dict]:
        """查询未解决的对账差异。"""
        self._check_auth(tenant_id, "wms:reconcile:execute")
        diffs = await self._diff_repo.list_open_diffs(self._session, tenant_id)
        return [
            {
                "diff_id": str(d.diff_id),
                "sku_id": str(d.sku_id),
                "warehouse_id": str(d.warehouse_id),
                "wms_quantity": float(d.wms_quantity),
                "inv_quantity": float(d.inv_quantity),
                "diff_quantity": float(d.diff_quantity),
                "diff_type": d.diff_type,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in diffs
        ]

    async def resolve_diff(
        self,
        tenant_id: UUID,
        diff_id: UUID,
        resolution_note: str,
        operated_by: UUID,
    ) -> dict:
        """解决对账差异。"""
        self._check_auth(tenant_id, "wms:reconcile:execute")
        await self._diff_repo.resolve(
            self._session, tenant_id, diff_id, resolution_note, datetime.now(timezone.utc)
        )
        return {"diff_id": str(diff_id), "status": "resolved"}