"""FIN 结算路由 - 6 个接口。"""


from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.fin.settlement_service import SettlementService
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.infrastructure.db.session import get_db_session
from app.interfaces.api.v1.fin.routes._deps import (
    get_settlement_service,
    get_tenant_id,
)
from app.interfaces.api.v1.fin.schemas.settlement_schemas import (
    SettlementCancelRequest,
    SettlementCreateRequest,
    SettlementCrossTenantConfirmRequest,
    SettlementLineResponse,
    SettlementListResponse,
    SettlementResponse,
)
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/settlements", tags=["EITP-FIN-001 Settlement"])


def _to_line_response(line) -> SettlementLineResponse:
    return SettlementLineResponse(
        line_no=line.line_no,
        product_id=line.product_id,
        quantity=line.quantity,
        tax_exclusive_unit_price=line.tax_exclusive_unit_price.amount,
        tax_inclusive_unit_price=line.tax_inclusive_unit_price.amount,
        tax_rate=line.tax_rate,
        line_amount=line.line_settlement_amount().amount,
        line_tax_amount=line.line_tax_amount().amount,
    )


def _to_response(settlement) -> SettlementResponse:
    return SettlementResponse(
        settlement_id=settlement.settlement_id,
        settlement_no=settlement.settlement_no,
        settlement_type=settlement.settlement_type.value,
        status=settlement.status.value,
        counterparty_id=settlement.counterparty_id,
        counterparty_type=settlement.counterparty_type,
        currency=settlement.currency,
        settlement_amount=settlement.settlement_amount.amount,
        tax_amount=settlement.tax_amount.amount,
        related_order_type=settlement.related_order_type,
        related_order_id=settlement.related_order_id,
        initiator_tenant_id=settlement.initiator_tenant_id,
        receiver_tenant_id=settlement.receiver_tenant_id,
        lines=[_to_line_response(ln) for ln in settlement.settlement_lines],
        created_at=settlement.created_at,
        updated_at=settlement.updated_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
@require_permission("fin:settlement:create")
async def create_settlement(
    req: SettlementCreateRequest,
    svc: SettlementService = Depends(get_settlement_service),
    session: AsyncSession = Depends(get_db_session),
) -> SettlementResponse:
    tenant_id = get_tenant_id()
    lines = [
        {
            "line_no": ln.line_no or idx,
            "product_id": ln.product_id,
            "quantity": ln.quantity,
            "tax_exclusive_unit_price": ln.tax_exclusive_unit_price,
            "tax_inclusive_unit_price": ln.tax_inclusive_unit_price,
            "tax_rate": ln.tax_rate,
        }
        for idx, ln in enumerate(req.lines, start=1)
    ]
    settlement = await svc.create_settlement(
        tenant_id=tenant_id,
        settlement_no=req.settlement_no,
        settlement_type=req.settlement_type,
        counterparty_id=req.counterparty_id,
        counterparty_type=req.counterparty_type,
        currency=req.currency,
        lines=lines,
        related_order_type=req.related_order_type,
        related_order_id=req.related_order_id,
        receiver_tenant_id=req.receiver_tenant_id,
    )
    await session.commit()
    return _to_response(settlement)


@router.post("/{settlement_no}/confirm")
@require_permission("fin:settlement:confirm")
async def confirm_settlement(
    settlement_no: str,
    svc: SettlementService = Depends(get_settlement_service),
    session: AsyncSession = Depends(get_db_session),
) -> SettlementResponse:
    tenant_id = get_tenant_id()
    confirmed = await svc.confirm_settlement(tenant_id, settlement_no)
    await session.commit()
    return _to_response(confirmed)


@router.post("/{settlement_no}/cancel")
@require_permission("fin:settlement:cancel")
async def cancel_settlement(
    settlement_no: str,
    req: SettlementCancelRequest,
    svc: SettlementService = Depends(get_settlement_service),
    session: AsyncSession = Depends(get_db_session),
) -> SettlementResponse:
    tenant_id = get_tenant_id()
    cancelled = await svc.cancel_settlement(tenant_id, settlement_no, req.reason)
    await session.commit()
    return _to_response(cancelled)


@router.get("/{settlement_no}")
@require_permission("fin:settlement:read")
async def get_settlement(
    settlement_no: str,
    svc: SettlementService = Depends(get_settlement_service),
) -> SettlementResponse:
    settlement = await svc._settlement_repo.get_by_no(settlement_no)
    if settlement is None:
        raise FINError(
            FINErrorCode.SETTLEMENT_NOT_FOUND,
            f"settlement {settlement_no} not found",
        )
    return _to_response(settlement)


@router.get("")
@require_permission("fin:settlement:read")
async def list_settlements(
    settlement_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    counterparty_id: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: SettlementService = Depends(get_settlement_service),
) -> SettlementListResponse:
    tenant_id = get_tenant_id()
    items = await svc._settlement_repo.list_settlements(
        tenant_id,
        status=status_filter,
        settlement_type=settlement_type,
        counterparty_id=counterparty_id,
        limit=limit,
        offset=offset,
    )
    return SettlementListResponse(
        items=[_to_response(s) for s in items],
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.post("/cross-tenant/{settlement_no}/confirm")
@require_permission("fin:settlement:cross-tenant-confirm")
async def confirm_cross_tenant_settlement(
    settlement_no: str,
    req: SettlementCrossTenantConfirmRequest,
    svc: SettlementService = Depends(get_settlement_service),
    session: AsyncSession = Depends(get_db_session),
) -> SettlementResponse:
    tenant_id = get_tenant_id()
    confirmed = await svc.confirm_cross_tenant_settlement(
        tenant_id=tenant_id,
        settlement_no=settlement_no,
        initiator_tenant_id=req.initiator_tenant_id,
        receiver_tenant_id=req.receiver_tenant_id,
    )
    await session.commit()
    return _to_response(confirmed)