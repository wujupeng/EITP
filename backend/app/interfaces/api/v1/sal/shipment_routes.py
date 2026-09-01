"""发货管理路由 - design 2.3.2.4，红线一：通过 WMS Picking/Shipping API。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sales.sal_app_services import ShipmentAppSvc
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.sal import CreateShipmentRequest, ShipmentConfirmRequest

router = APIRouter(prefix="/sal/shipments", tags=["sal-shipment"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


@router.post("")
@require_permission("sal:shipment:create")
async def create_shipment(req: CreateShipmentRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = ShipmentAppSvc(session)
    lines = [
        {"order_line_id": str(l.order_line_id), "enterprise_sku_id": str(l.enterprise_sku_id),
         "ship_quantity": l.ship_quantity}
        for l in req.lines
    ]
    orm = await svc.create_shipment(
        tenant_id, req.shipment_code, req.order_ids, req.shipping_warehouse_id, lines,
        req.picking_strategy, req.idempotency_key,
    )
    await session.commit()
    return {"shipment_id": str(orm.shipment_id), "shipment_code": orm.shipment_code, "status": orm.status}


@router.get("")
@require_permission("sal:shipment:create")
async def list_shipments(
    status: str | None = Query(None), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = ShipmentAppSvc(session)
    items = await svc.list_shipments(tenant_id, status, offset, limit)
    return [
        {"shipment_id": str(s.shipment_id), "shipment_code": s.shipment_code,
         "status": s.status, "logistics_no": s.logistics_no}
        for s in items
    ]


@router.get("/{shipment_id}")
@require_permission("sal:shipment:create")
async def get_shipment(shipment_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = ShipmentAppSvc(session)
    orm = await svc.get_shipment(tenant_id, shipment_id)
    lines = await svc._repo.list_lines(session, tenant_id, shipment_id)
    return {
        "shipment_id": str(orm.shipment_id), "shipment_code": orm.shipment_code,
        "order_ids": orm.order_ids, "shipping_warehouse_id": str(orm.shipping_warehouse_id),
        "status": orm.status, "logistics_no": orm.logistics_no, "carrier": orm.carrier,
        "wms_picking_task_id": str(orm.wms_picking_task_id) if orm.wms_picking_task_id else None,
        "wms_shipping_id": str(orm.wms_shipping_id) if orm.wms_shipping_id else None,
        "inv_transaction_ids": orm.inv_transaction_ids,
        "lines": [
            {"line_id": str(l.line_id), "order_line_id": str(l.order_line_id),
             "enterprise_sku_id": str(l.enterprise_sku_id), "ship_quantity": float(l.ship_quantity)}
            for l in lines
        ],
    }


@router.post("/{shipment_id}/submit")
@require_permission("sal:shipment:create")
async def submit_shipment(shipment_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = ShipmentAppSvc(session)
    orm = await svc.submit_shipment(tenant_id, shipment_id)
    await session.commit()
    return {"shipment_id": str(orm.shipment_id), "status": orm.status,
            "wms_picking_task_id": str(orm.wms_picking_task_id) if orm.wms_picking_task_id else None}


@router.post("/{shipment_id}/confirm")
@require_permission("sal:shipment:confirm")
async def confirm_shipment(shipment_id: UUID, req: ShipmentConfirmRequest, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = ShipmentAppSvc(session)
    orm = await svc.confirm_shipment(tenant_id, shipment_id, req.logistics_no, req.carrier, req.idempotency_key)
    await session.commit()
    return {"shipment_id": str(orm.shipment_id), "status": orm.status,
            "wms_shipping_id": str(orm.wms_shipping_id) if orm.wms_shipping_id else None,
            "inv_transaction_ids": orm.inv_transaction_ids}


@router.post("/{shipment_id}/cancel")
@require_permission("sal:shipment:create")
async def cancel_shipment(shipment_id: UUID, session: AsyncSession = Depends(get_db_session)) -> dict:
    tenant_id = _get_tenant_id()
    svc = ShipmentAppSvc(session)
    orm = await svc.cancel_shipment(tenant_id, shipment_id)
    await session.commit()
    return {"shipment_id": str(orm.shipment_id), "status": orm.status}