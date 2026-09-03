"""FIN 对账路由 - 5 个接口。"""


from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.fin.reconciliation_service import ReconciliationService
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.infrastructure.db.session import get_db_session
from app.interfaces.api.v1.fin.routes._deps import (
    get_reconciliation_service,
    get_tenant_id,
)
from app.interfaces.api.v1.fin.schemas.reconciliation_schemas import (
    ReconciliationCreateRequest,
    ReconciliationDifferenceHandleRequest,
    ReconciliationListResponse,
    ReconciliationReportResponse,
    ReconciliationResponse,
)
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/reconciliations", tags=["EITP-FIN-001 Reconciliation"])


def _to_response(recon) -> ReconciliationResponse:
    return ReconciliationResponse(
        recon_id=recon.recon_id,
        recon_no=recon.recon_no,
        period_start=recon.period_start,
        period_end=recon.period_end,
        scope_type=recon.scope_type,
        scope_value=recon.scope_value,
        data_source=recon.data_source,
        currency=recon.system_amount.currency,
        status=recon.status.value,
        system_amount=recon.system_amount.amount,
        external_amount=recon.external_amount.amount,
        matched_count=recon.matched_count,
        diff_count=recon.diff_count,
        created_at=recon.created_at,
        updated_at=recon.updated_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
@require_permission("fin:reconciliation:create")
async def create_reconciliation(
    req: ReconciliationCreateRequest,
    svc: ReconciliationService = Depends(get_reconciliation_service),
    session: AsyncSession = Depends(get_db_session),
) -> ReconciliationResponse:
    tenant_id = get_tenant_id()
    lines = None
    if req.lines is not None:
        lines = [
            {
                "line_no": ln.line_no or idx,
                "business_ref_type": ln.business_ref_type,
                "business_ref_id": ln.business_ref_id,
                "system_amount": ln.system_amount,
                "external_amount": ln.external_amount,
                "is_matched": ln.is_matched,
            }
            for idx, ln in enumerate(req.lines, start=1)
        ]
    recon = await svc.create_reconciliation(
        tenant_id=tenant_id,
        recon_no=req.recon_no,
        period_start=req.period_start,
        period_end=req.period_end,
        scope_type=req.scope_type,
        scope_value=req.scope_value,
        data_source=req.data_source,
        currency=req.currency,
        lines=lines,
    )
    await session.commit()
    return _to_response(recon)


@router.post("/{recon_no}/differences/{diff_id}/handle")
@require_permission("fin:reconciliation:handle-diff")
async def handle_difference(
    recon_no: str,
    diff_id: UUID,
    req: ReconciliationDifferenceHandleRequest,
    svc: ReconciliationService = Depends(get_reconciliation_service),
    session: AsyncSession = Depends(get_db_session),
) -> ReconciliationResponse:
    tenant_id = get_tenant_id()
    handled = await svc.handle_difference(
        tenant_id=tenant_id,
        recon_no=recon_no,
        diff_id=diff_id,
        handle_action=req.handle_action,
        handler_id=req.handler_id,
        handle_opinion=req.handle_opinion,
    )
    await session.commit()
    return _to_response(handled)


@router.get("/{recon_no}/report")
@require_permission("fin:reconciliation:read")
async def get_recon_report(
    recon_no: str,
    svc: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationReportResponse:
    tenant_id = get_tenant_id()
    report = await svc.get_recon_report(tenant_id, recon_no)
    return ReconciliationReportResponse(**report)


@router.get("/{recon_no}")
@require_permission("fin:reconciliation:read")
async def get_reconciliation(
    recon_no: str,
    svc: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationResponse:
    recon = await svc._recon_repo.get_by_no(recon_no)
    if recon is None:
        raise FINError(
            FINErrorCode.RECON_NOT_FOUND,
            f"reconciliation {recon_no} not found",
        )
    return _to_response(recon)


@router.get("")
@require_permission("fin:reconciliation:read")
async def list_reconciliations(
    status_filter: str | None = Query(None, alias="status"),
    scope_type: str | None = Query(None),
    scope_value: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationListResponse:
    tenant_id = get_tenant_id()
    items = await svc._recon_repo.list_reconciliations(
        tenant_id,
        status=status_filter,
        scope_type=scope_type,
        limit=limit,
        offset=offset,
    )
    return ReconciliationListResponse(
        items=[_to_response(r) for r in items],
        total=len(items),
        offset=offset,
        limit=limit,
    )