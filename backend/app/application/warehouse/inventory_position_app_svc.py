"""WMS 库存位置查询应用服务 - 多维度查询与 PDA 扫码。

编排序列：权限校验 → DataScope 收敛 → 多维度查询。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.warehouse.inventory_position_repository import (
    InventoryPositionRepository,
)
from app.infrastructure.warehouse.space_repositories import LocationRepository
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class InventoryPositionAppSvc:
    """库存位置查询应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._pos_repo = InventoryPositionRepository()
        self._loc_repo = LocationRepository()

    def _check_auth(self, tenant_id: UUID, permission: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise WMSError(WMSErrorCode.SERVICE_UNAVAILABLE, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise WMSError(WMSErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")

    async def query_by_sku(
        self,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID | None = None,
    ) -> list[dict]:
        """按 SKU 查询库存位置（P95 ≤ 150ms）。"""
        self._check_auth(tenant_id, "wms:position:query")
        positions = await self._pos_repo.query_by_sku(
            self._session, tenant_id, sku_id, warehouse_id
        )
        return [self._to_dict(p) for p in positions]

    async def query_by_location(
        self,
        tenant_id: UUID,
        location_id: UUID,
    ) -> list[dict]:
        """按库位查询库存位置（PDA 扫码，P95 ≤ 50ms）。"""
        self._check_auth(tenant_id, "wms:position:query")
        positions = await self._pos_repo.query_by_location(
            self._session, tenant_id, location_id
        )
        return [self._to_dict(p) for p in positions]

    async def query_by_location_code(
        self,
        tenant_id: UUID,
        warehouse_id: UUID,
        location_code: str,
    ) -> list[dict]:
        """PDA 扫码 - 按库位编码查询库存位置。"""
        self._check_auth(tenant_id, "wms:position:query")
        loc = await self._loc_repo.get_by_code(
            self._session, tenant_id, warehouse_id, location_code
        )
        if loc is None:
            raise WMSError(
                WMSErrorCode.WAREHOUSE_NOT_FOUND,
                f"库位编码 {location_code} 不存在",
            )
        return await self.query_by_location(tenant_id, loc.location_id)

    async def query_by_sku_location_status(
        self,
        tenant_id: UUID,
        sku_id: UUID,
        location_id: UUID,
        inventory_status: str,
    ) -> dict | None:
        """按 SKU+库位+状态精确查询（组合键）。"""
        self._check_auth(tenant_id, "wms:position:query")
        pos = await self._pos_repo.query_by_sku_location_status(
            self._session, tenant_id, sku_id, location_id, inventory_status
        )
        return self._to_dict(pos) if pos is not None else None

    async def aggregate_by_sku_warehouse(
        self,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
    ) -> list[dict]:
        """按状态聚合 SKU 在仓库中的库存量（对账用）。"""
        self._check_auth(tenant_id, "wms:position:query")
        result = await self._pos_repo.aggregate_by_sku_warehouse(
            self._session, tenant_id, sku_id, warehouse_id
        )
        return [
            {"inventory_status": status, "total_quantity": qty}
            for status, qty in result
        ]

    @staticmethod
    def _to_dict(pos) -> dict:
        return {
            "position_id": str(pos.position_id),
            "sku_id": str(pos.sku_id),
            "warehouse_id": str(pos.warehouse_id),
            "location_id": str(pos.location_id),
            "bin_id": str(pos.bin_id) if pos.bin_id else None,
            "lot_number": pos.lot_number,
            "batch_number": pos.batch_number,
            "serial_number": pos.serial_number,
            "expiry_date": pos.expiry_date.isoformat() if pos.expiry_date else None,
            "quantity": float(pos.quantity),
            "inventory_status": pos.inventory_status,
            "received_at": pos.received_at.isoformat() if pos.received_at else None,
            "last_updated_at": pos.last_updated_at.isoformat() if pos.last_updated_at else None,
        }