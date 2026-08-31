"""采购到货路由 - 第一条红线：收货确认通过 WMS Receiving API 触发收货。"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.purchasing.pur_app_services import PurchaseReceiptAppSvc
from app.infrastructure.db.session import get_db_session
from app.infrastructure.purchasing.models import PurPurchaseReceiptLineORM, PurPurchaseReceiptORM
from app.infrastructure.purchasing.repositories import PurchaseReceiptRepository
from app.interfaces.middleware.permission_interceptor import require_permission
from app.interfaces.middleware.security_context import SecurityContext
from app.interfaces.schemas.pur import (
    CreateReceiptRequest,
    QcResultRequest,
    ReceiptConfirmRequest,
)

router = APIRouter(prefix="/pur/receipts", tags=["pur-receipt"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


@router.post("")
@require_permission("pur:receipt:execute")
async def create_receipt(
    req: CreateReceiptRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    orm = PurPurchaseReceiptORM(
        tenant_id=tenant_id, receipt_code=req.receipt_code, order_id=req.order_id,
        asn_id=req.asn_id, supplier_id=req.supplier_id, warehouse_id=req.warehouse_id,
        status="pending",
    )
    repo = PurchaseReceiptRepository()
    orm = await repo.save(session, orm)
    await session.commit()
    return {"receipt_id": str(orm.receipt_id), "receipt_code": orm.receipt_code, "status": orm.status}


@router.post("/{receipt_id}/confirm")
@require_permission("pur:receipt:execute")
async def confirm_receipt(
    receipt_id: UUID,
    req: ReceiptConfirmRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = PurchaseReceiptAppSvc(session)
    orm = await svc._repo.get_by_id(session, tenant_id, receipt_id)
    if orm is None:
        return {"error": "not_found"}

    _idempotency_key = req.idempotency_key or str(uuid4())
    wms_receiving_id = None
    inv_tx_ids: list[str] = []

    for line in req.lines:
        wms_result = await svc.trigger_wms_receiving(
            tenant_id, orm.order_id, orm.warehouse_id, req.receiving_zone_id,
            line.sku_id, line.received_quantity, line.location_id, user_id,
        )
        wms_receiving_id = wms_result.get("receiving_id", wms_receiving_id)
        inv_tx_ids.extend(wms_result.get("inv_transaction_ids", []))
        receipt_line = PurPurchaseReceiptLineORM(
            tenant_id=tenant_id, receipt_id=receipt_id,
            order_line_id=line.order_line_id, sku_id=line.sku_id,
            received_quantity=line.received_quantity, qc_result="pending",
            wms_receiving_id=UUID(wms_receiving_id) if wms_receiving_id else None,
        )
        session.add(receipt_line)

    orm = await svc.confirm_receipt(tenant_id, receipt_id, UUID(wms_receiving_id) if wms_receiving_id else UUID(int=0), inv_tx_ids)
    await session.commit()
    return {
        "receipt_id": str(orm.receipt_id), "status": orm.status,
        "wms_receiving_id": str(orm.wms_receiving_id) if orm.wms_receiving_id else None,
        "inv_transaction_ids": orm.inv_transaction_ids,
    }


@router.post("/{receipt_id}/qc")
@require_permission("pur:receipt:execute")
async def record_qc(
    receipt_id: UUID,
    req: QcResultRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    repo = PurchaseReceiptRepository()
    lines = await repo.list_lines(session, tenant_id, receipt_id)
    for line in lines:
        if line.line_id == req.line_id:
            line.qc_result = req.qc_result
            break
    await session.flush()
    await session.commit()
    return {"receipt_id": str(receipt_id), "line_id": str(req.line_id), "qc_result": req.qc_result}


@router.get("/{receipt_id}")
@require_permission("pur:receipt:query")
async def get_receipt(
    receipt_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    repo = PurchaseReceiptRepository()
    orm = await repo.get_by_id(session, tenant_id, receipt_id)
    if orm is None:
        return {"error": "not_found"}
    lines = await repo.list_lines(session, tenant_id, receipt_id)
    return {
        "receipt_id": str(orm.receipt_id), "receipt_code": orm.receipt_code,
        "order_id": str(orm.order_id), "status": orm.status,
        "wms_receiving_id": str(orm.wms_receiving_id) if orm.wms_receiving_id else None,
        "inv_transaction_ids": orm.inv_transaction_ids,
        "lines": [
            {"line_id": str(l.line_id), "sku_id": str(l.sku_id),
             "received_quantity": float(l.received_quantity), "qc_result": l.qc_result}
            for l in lines
        ],
    }