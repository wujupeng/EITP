"""FIN 发票路由 - 7 个接口。"""


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.fin.invoice_service import InvoiceService
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.infrastructure.db.session import get_db_session
from app.interfaces.api.v1.fin.routes._deps import (
    get_invoice_service,
    get_tenant_id,
)
from app.interfaces.api.v1.fin.schemas.invoice_schemas import (
    InvoiceArchiveRequest,
    InvoiceIssueRequest,
    InvoiceLineResponse,
    InvoiceListResponse,
    InvoiceMatchRequest,
    InvoiceMatchResponse,
    InvoiceResponse,
    InvoiceVoidRequest,
    InvoiceVerifyRequest,
)
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/invoices", tags=["EITP-FIN-001 Invoice"])


def _to_line_response(line) -> InvoiceLineResponse:
    return InvoiceLineResponse(
        line_no=line.line_no,
        product_id=line.product_id,
        product_name=line.product_name,
        quantity=line.quantity,
        tax_exclusive_amount=line.tax_exclusive_amount.amount,
        tax_amount=line.tax_amount.amount,
        tax_inclusive_amount=line.tax_inclusive_amount.amount,
    )


def _to_response(invoice) -> InvoiceResponse:
    return InvoiceResponse(
        invoice_id=invoice.invoice_id,
        invoice_code=invoice.invoice_code,
        invoice_no=invoice.invoice_no,
        invoice_type=invoice.invoice_type.value,
        status=invoice.status.value,
        buyer_info=invoice.buyer_info,
        seller_info=invoice.seller_info,
        currency=invoice.tax_inclusive_amount.currency,
        tax_exclusive_amount=invoice.tax_exclusive_amount.amount,
        tax_amount=invoice.tax_amount.amount,
        tax_inclusive_amount=invoice.tax_inclusive_amount.amount,
        archive_hash=invoice.archive_hash,
        image_storage_id=invoice.image_storage_id,
        red_original_invoice_no=invoice.red_original_invoice_no,
        lines=[_to_line_response(ln) for ln in invoice.invoice_lines],
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
@require_permission("fin:invoice:issue")
async def issue_invoice(
    req: InvoiceIssueRequest,
    svc: InvoiceService = Depends(get_invoice_service),
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceResponse:
    tenant_id = get_tenant_id()
    lines = [
        {
            "line_no": ln.line_no or idx,
            "product_id": ln.product_id,
            "product_name": ln.product_name,
            "quantity": ln.quantity,
            "tax_exclusive_amount": ln.tax_exclusive_amount,
            "tax_amount": ln.tax_amount,
            "tax_inclusive_amount": ln.tax_inclusive_amount,
        }
        for idx, ln in enumerate(req.lines, start=1)
    ]
    invoice = await svc.issue_invoice(
        tenant_id=tenant_id,
        invoice_code=req.invoice_code,
        invoice_no=req.invoice_no,
        invoice_type=req.invoice_type,
        buyer_info=req.buyer_info,
        seller_info=req.seller_info,
        lines=lines,
        currency=req.currency,
        red_original_invoice_no=req.red_original_invoice_no,
        image_storage_id=req.image_storage_id,
    )
    await session.commit()
    return _to_response(invoice)


@router.post("/{invoice_no}/match")
@require_permission("fin:invoice:match")
async def match_invoice(
    invoice_no: str,
    req: InvoiceMatchRequest,
    svc: InvoiceService = Depends(get_invoice_service),
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceMatchResponse:
    tenant_id = get_tenant_id()
    candidates = [c.model_dump() for c in req.candidates]
    result = await svc.match_invoice(tenant_id, invoice_no, candidates)
    await session.commit()
    return InvoiceMatchResponse(
        business_ref_type=result.business_ref_type or "",
        business_ref_id=result.business_ref_id or "",
        score=result.score,
    )


@router.post("/{invoice_no}/verify")
@require_permission("fin:invoice:verify")
async def verify_invoice(
    invoice_no: str,
    req: InvoiceVerifyRequest,
    svc: InvoiceService = Depends(get_invoice_service),
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceResponse:
    tenant_id = get_tenant_id()
    verified = await svc.verify_invoice(tenant_id, invoice_no)
    await session.commit()
    return _to_response(verified)


@router.post("/{invoice_no}/archive")
@require_permission("fin:invoice:archive")
async def archive_invoice(
    invoice_no: str,
    req: InvoiceArchiveRequest,
    svc: InvoiceService = Depends(get_invoice_service),
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceResponse:
    tenant_id = get_tenant_id()
    archived = await svc.archive_invoice(tenant_id, invoice_no)
    await session.commit()
    return _to_response(archived)


@router.post("/{invoice_no}/void")
@require_permission("fin:invoice:void")
async def void_invoice(
    invoice_no: str,
    req: InvoiceVoidRequest,
    svc: InvoiceService = Depends(get_invoice_service),
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceResponse:
    tenant_id = get_tenant_id()
    voided = await svc.void_invoice(tenant_id, invoice_no, req.reason)
    await session.commit()
    return _to_response(voided)


@router.get("/{invoice_no}")
@require_permission("fin:invoice:read")
async def get_invoice(
    invoice_no: str,
    svc: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    invoice = await svc._invoice_repo.get_by_no(invoice_no)
    if invoice is None:
        raise FINError(
            FINErrorCode.INVOICE_NOT_FOUND,
            f"invoice {invoice_no} not found",
        )
    return _to_response(invoice)


@router.get("")
@require_permission("fin:invoice:read")
async def list_invoices(
    invoice_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: InvoiceService = Depends(get_invoice_service),
) -> InvoiceListResponse:
    tenant_id = get_tenant_id()
    items = await svc._invoice_repo.list_invoices(
        tenant_id,
        status=status_filter,
        invoice_type=invoice_type,
        limit=limit,
        offset=offset,
    )
    return InvoiceListResponse(
        items=[_to_response(i) for i in items],
        total=len(items),
        offset=offset,
        limit=limit,
    )