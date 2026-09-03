"""FIN 付款路由 - 7 个接口。"""


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.fin.payment_service import PaymentService
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.infrastructure.db.session import get_db_session
from app.interfaces.api.v1.fin.routes._deps import (
    get_payment_service,
    get_tenant_id,
)
from app.interfaces.api.v1.fin.schemas.payment_schemas import (
    BankStatementImportRequest,
    BankStatementImportResponse,
    PaymentApproveRequest,
    PaymentBankCallbackRequest,
    PaymentCreateRequest,
    PaymentListResponse,
    PaymentResponse,
)
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/payments", tags=["EITP-FIN-001 Payment"])


def _to_response(payment) -> PaymentResponse:
    return PaymentResponse(
        payment_id=payment.payment_id,
        payment_no=payment.payment_no,
        ap_voucher_no=payment.ap_voucher_no,
        payment_amount=payment.payment_amount.amount,
        currency=payment.payment_amount.currency,
        payment_method=payment.payment_method.value,
        payment_account=payment.payment_account,
        payee_account=payment.payee_account,
        status=payment.status.value,
        approver_id=payment.approver_id,
        approval_opinion=payment.approval_opinion,
        bank_ref=payment.bank_ref,
        expected_payment_date=payment.expected_payment_date,
        actual_payment_date=payment.actual_payment_date,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
@require_permission("fin:payment:request")
async def request_payment(
    req: PaymentCreateRequest,
    svc: PaymentService = Depends(get_payment_service),
    session: AsyncSession = Depends(get_db_session),
) -> PaymentResponse:
    tenant_id = get_tenant_id()
    payment = await svc.request_payment(
        tenant_id=tenant_id,
        payment_no=req.payment_no,
        ap_voucher_no=req.ap_voucher_no,
        payment_amount=req.payment_amount,
        payment_method=req.payment_method,
        payment_account=req.payment_account,
        payee_account=req.payee_account,
        currency=req.currency,
        expected_payment_date=req.expected_payment_date,
    )
    await session.commit()
    return _to_response(payment)


@router.post("/{payment_no}/approve")
@require_permission("fin:payment:approve")
async def approve_payment(
    payment_no: str,
    req: PaymentApproveRequest,
    svc: PaymentService = Depends(get_payment_service),
    session: AsyncSession = Depends(get_db_session),
) -> PaymentResponse:
    tenant_id = get_tenant_id()
    if req.approved:
        result = await svc.approve_payment(
            tenant_id, payment_no, req.approver_id, req.approval_opinion
        )
    else:
        result = await svc.reject_payment(
            tenant_id, payment_no, req.approver_id, req.approval_opinion
        )
    await session.commit()
    return _to_response(result)


@router.post("/{payment_no}/execute")
@require_permission("fin:payment:execute")
async def execute_payment(
    payment_no: str,
    svc: PaymentService = Depends(get_payment_service),
    session: AsyncSession = Depends(get_db_session),
) -> PaymentResponse:
    tenant_id = get_tenant_id()
    executing = await svc.execute_payment(tenant_id, payment_no)
    await session.commit()
    return _to_response(executing)


@router.post("/{payment_no}/bank-callback")
@require_permission("fin:payment:bank-callback")
async def bank_callback(
    payment_no: str,
    req: PaymentBankCallbackRequest,
    svc: PaymentService = Depends(get_payment_service),
    session: AsyncSession = Depends(get_db_session),
) -> PaymentResponse:
    result = await svc.bank_callback(payment_no, req.callback_payload)
    await session.commit()
    return _to_response(result)


@router.get("/{payment_no}")
@require_permission("fin:payment:read")
async def get_payment(
    payment_no: str,
    svc: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    payment = await svc._payment_repo.get_by_no(payment_no)
    if payment is None:
        raise FINError(
            FINErrorCode.PAYMENT_NOT_FOUND,
            f"payment {payment_no} not found",
        )
    return _to_response(payment)


@router.get("")
@require_permission("fin:payment:read")
async def list_payments(
    status_filter: str | None = Query(None, alias="status"),
    ap_voucher_no: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    tenant_id = get_tenant_id()
    items = await svc._payment_repo.list_payments(
        tenant_id,
        status=status_filter,
        ap_voucher_no=ap_voucher_no,
        limit=limit,
        offset=offset,
    )
    return PaymentListResponse(
        items=[_to_response(p) for p in items],
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.post("/bank-statement/import")
@require_permission("fin:payment:bank-statement-import")
async def import_bank_statements(
    req: BankStatementImportRequest,
    svc: PaymentService = Depends(get_payment_service),
    session: AsyncSession = Depends(get_db_session),
) -> BankStatementImportResponse:
    tenant_id = get_tenant_id()
    imported = await svc.import_bank_statements(tenant_id, req.statements)
    await session.commit()
    return BankStatementImportResponse(
        imported_count=len(imported),
        items=imported,
    )