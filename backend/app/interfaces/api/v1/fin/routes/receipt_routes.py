"""FIN 收款路由 - 6 个接口。"""


from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.fin.receipt_service import ReceiptService
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.infrastructure.db.session import get_db_session
from app.interfaces.api.v1.fin.routes._deps import (
    get_receipt_service,
    get_tenant_id,
)
from app.interfaces.api.v1.fin.schemas.receipt_schemas import (
    CollectionTaskHandleRequest,
    CollectionTaskListResponse,
    CollectionTaskResponse,
    ReceiptConfirmRequest,
    ReceiptListResponse,
    ReceiptResponse,
    ReceiptWriteOffRequest,
)
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/receipts", tags=["EITP-FIN-001 Receipt"])
collection_router = APIRouter(
    prefix="/collection-tasks", tags=["EITP-FIN-001 Collection"]
)


def _write_off_total(receipt) -> Decimal:
    return sum(
        (ln.write_off_amount.amount for ln in receipt.write_off_lines),
        start=Decimal("0"),
    )


def _to_response(receipt) -> ReceiptResponse:
    return ReceiptResponse(
        receipt_id=receipt.receipt_id,
        receipt_no=receipt.receipt_no,
        receipt_amount=receipt.receipt_amount.amount,
        currency=receipt.receipt_amount.currency,
        status=receipt.status.value,
        receiver_account=receipt.receiver_account,
        payer_account=receipt.payer_account,
        bank_ref=receipt.bank_ref,
        write_off_amount=_write_off_total(receipt),
        arrival_time=receipt.arrival_time,
        created_at=receipt.created_at,
        updated_at=receipt.updated_at,
    )


def _to_task_response(task) -> CollectionTaskResponse:
    return CollectionTaskResponse(
        task_id=task.task_id,
        ar_voucher_no=task.ar_voucher_no,
        stage=task.collection_stage.value,
        status=task.status.value,
        overdue_amount=task.overdue_amount.amount,
        overdue_days=task.overdue_days,
        record_count=len(task.records),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
@require_permission("fin:receipt:confirm")
async def confirm_receipt(
    receipt_no: str,
    req: ReceiptConfirmRequest,
    svc: ReceiptService = Depends(get_receipt_service),
    session: AsyncSession = Depends(get_db_session),
) -> ReceiptResponse:
    tenant_id = get_tenant_id()
    confirmed = await svc.confirm_receipt(tenant_id, receipt_no)
    await session.commit()
    return _to_response(confirmed)


@router.post("/{receipt_no}/write-off")
@require_permission("fin:receipt:write-off")
async def write_off_receipt(
    receipt_no: str,
    req: ReceiptWriteOffRequest,
    svc: ReceiptService = Depends(get_receipt_service),
    session: AsyncSession = Depends(get_db_session),
) -> ReceiptResponse:
    tenant_id = get_tenant_id()
    lines = [
        {
            "line_no": ln.line_no or idx,
            "ar_voucher_no": ln.ar_voucher_no,
            "write_off_amount": ln.write_off_amount,
        }
        for idx, ln in enumerate(req.write_off_lines, start=1)
    ]
    written_off = await svc.write_off_receipt(tenant_id, receipt_no, lines)
    await session.commit()
    return _to_response(written_off)


@router.get("/{receipt_no}")
@require_permission("fin:receipt:read")
async def get_receipt(
    receipt_no: str,
    svc: ReceiptService = Depends(get_receipt_service),
) -> ReceiptResponse:
    receipt = await svc._receipt_repo.get_by_no(receipt_no)
    if receipt is None:
        raise FINError(
            FINErrorCode.RECEIPT_NOT_FOUND,
            f"receipt {receipt_no} not found",
        )
    return _to_response(receipt)


@router.get("")
@require_permission("fin:receipt:read")
async def list_receipts(
    status_filter: str | None = Query(None, alias="status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: ReceiptService = Depends(get_receipt_service),
) -> ReceiptListResponse:
    tenant_id = get_tenant_id()
    items = await svc._receipt_repo.list_receipts(
        tenant_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return ReceiptListResponse(
        items=[_to_response(r) for r in items],
        total=len(items),
        offset=offset,
        limit=limit,
    )


@collection_router.get("")
@require_permission("fin:collection:read")
async def list_collection_tasks(
    stage: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: ReceiptService = Depends(get_receipt_service),
) -> CollectionTaskListResponse:
    tenant_id = get_tenant_id()
    items = await svc._collection_task_repo.list_tasks(
        tenant_id,
        status=status_filter,
        stage=stage,
        limit=limit,
        offset=offset,
    )
    return CollectionTaskListResponse(
        items=[_to_task_response(t) for t in items],
        total=len(items),
        offset=offset,
        limit=limit,
    )


@collection_router.post("/{task_id}/handle")
@require_permission("fin:collection:handle")
async def handle_collection_task(
    task_id: UUID,
    req: CollectionTaskHandleRequest,
    svc: ReceiptService = Depends(get_receipt_service),
    session: AsyncSession = Depends(get_db_session),
) -> CollectionTaskResponse:
    tenant_id = get_tenant_id()
    handled = await svc.handle_collection_task(
        tenant_id=tenant_id,
        task_id=task_id,
        handler_id=req.handler_id,
        content=req.content,
        stage=req.stage,
    )
    await session.commit()
    return _to_task_response(handled)