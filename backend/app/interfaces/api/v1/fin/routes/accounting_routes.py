"""FIN 会计核算路由 - 8 个接口。"""


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.fin.accounting_service import AccountingService
from app.infrastructure.db.session import get_db_session
from app.interfaces.api.v1.fin.routes._deps import (
    get_accounting_service,
    get_tenant_id,
)
from app.interfaces.api.v1.fin.schemas.accounting_schemas import (
    APVoucherListQuery,
    APVoucherResponse,
    ARVoucherListQuery,
    ARVoucherResponse,
    AgingAnalysisQuery,
    AgingAnalysisResponse,
    FinancialReportResponse,
    GLAccountCreateRequest,
    GLAccountListQuery,
    GLAccountResponse,
    GLRedVoucherRequest,
    GLVoucherCreateRequest,
    GLVoucherListResponse,
    GLVoucherResponse,
    PeriodCloseRequest,
    PeriodCloseResponse,
)
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/accounting", tags=["EITP-FIN-001 Accounting"])


@router.get("/ar-vouchers")
@require_permission("fin:accounting:ar-read")
async def list_ar_vouchers(
    query: ARVoucherListQuery = Depends(),
    svc: AccountingService = Depends(get_accounting_service),
) -> list[ARVoucherResponse]:
    tenant_id = get_tenant_id()
    items = await svc.list_ar_vouchers(
        tenant_id,
        status=query.status,
        is_overdue=query.is_overdue,
        business_ref_type=query.business_ref_type,
        business_ref_id=query.business_ref_id,
        limit=query.limit,
        offset=query.offset,
    )
    return [ARVoucherResponse(**item) for item in items]


@router.get("/ap-vouchers")
@require_permission("fin:accounting:ap-read")
async def list_ap_vouchers(
    query: APVoucherListQuery = Depends(),
    svc: AccountingService = Depends(get_accounting_service),
) -> list[APVoucherResponse]:
    tenant_id = get_tenant_id()
    items = await svc.list_ap_vouchers(
        tenant_id,
        status=query.status,
        is_overdue=query.is_overdue,
        business_ref_type=query.business_ref_type,
        business_ref_id=query.business_ref_id,
        limit=query.limit,
        offset=query.offset,
    )
    return [APVoucherResponse(**item) for item in items]


@router.get("/aging-analysis")
@require_permission("fin:accounting:aging-read")
async def get_aging_analysis(
    query: AgingAnalysisQuery = Depends(),
    svc: AccountingService = Depends(get_accounting_service),
) -> AgingAnalysisResponse:
    tenant_id = get_tenant_id()
    result = await svc.get_aging_analysis(tenant_id, query.as_of_date)
    return AgingAnalysisResponse(**result)


@router.post("/gl-accounts", status_code=status.HTTP_201_CREATED)
@require_permission("fin:accounting:gl-account-create")
async def create_gl_account(
    req: GLAccountCreateRequest,
    svc: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_db_session),
) -> GLAccountResponse:
    tenant_id = get_tenant_id()
    account = await svc.create_gl_account(
        tenant_id=tenant_id,
        account_code=req.account_code,
        account_name=req.account_name,
        category=req.category,
        balance_direction=req.balance_direction,
        parent_code=req.parent_code,
        opening_balance=req.opening_balance,
    )
    await session.commit()
    return GLAccountResponse(
        account_id=account.account_id,
        account_code=account.account_code,
        account_name=account.account_name,
        category=account.category.value,
        balance_direction=account.balance_direction.value,
        parent_code=account.parent_code,
        opening_balance=account.opening_balance,
        period_debit=account.period_debit,
        period_credit=account.period_credit,
        closing_balance=account.closing_balance,
    )


@router.get("/gl-accounts")
@require_permission("fin:accounting:gl-account-read")
async def list_gl_accounts(
    query: GLAccountListQuery = Depends(),
    svc: AccountingService = Depends(get_accounting_service),
) -> list[GLAccountResponse]:
    tenant_id = get_tenant_id()
    items = await svc.list_gl_accounts(
        tenant_id,
        category=query.category,
        limit=query.limit,
        offset=query.offset,
    )
    return [GLAccountResponse(**item) for item in items]


@router.get("/gl-vouchers")
@require_permission("fin:accounting:gl-voucher-create")
async def list_gl_vouchers(
    period: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: AccountingService = Depends(get_accounting_service),
) -> GLVoucherListResponse:
    tenant_id = get_tenant_id()
    items = await svc.list_gl_vouchers(
        tenant_id, period=period, limit=limit, offset=offset
    )
    return GLVoucherListResponse(
        items=[GLVoucherResponse(**item) for item in items],
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.post("/gl-vouchers", status_code=status.HTTP_201_CREATED)
@require_permission("fin:accounting:gl-voucher-create")
async def create_gl_voucher(
    req: GLVoucherCreateRequest,
    svc: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_db_session),
) -> GLVoucherResponse:
    tenant_id = get_tenant_id()
    lines = [
        {
            "line_no": ln.line_no or idx,
            "account_code": ln.account_code,
            "debit_amount": ln.debit_amount,
            "credit_amount": ln.credit_amount,
        }
        for idx, ln in enumerate(req.lines, start=1)
    ]
    voucher = await svc.create_gl_voucher(
        tenant_id=tenant_id,
        voucher_no=req.voucher_no,
        voucher_date=req.voucher_date,
        summary=req.summary,
        period=req.period,
        lines=lines,
        business_ref_type=req.business_ref_type,
        business_ref_id=req.business_ref_id,
    )
    await session.commit()
    return GLVoucherResponse(
        voucher_id=voucher.gl_voucher_id,
        voucher_no=voucher.voucher_no,
        voucher_date=voucher.voucher_date,
        summary=voucher.summary,
        period=voucher.period,
        is_period_closed=voucher.is_period_closed,
        red_original_voucher_no=voucher.red_original_voucher_no,
        business_ref_type=voucher.business_ref_type,
        business_ref_id=voucher.business_ref_id,
        created_at=voucher.created_at,
    )


@router.post("/gl-vouchers/{original_voucher_no}/red")
@require_permission("fin:accounting:gl-voucher-red")
async def red_voucher(
    original_voucher_no: str,
    req: GLRedVoucherRequest,
    svc: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_db_session),
) -> GLVoucherResponse:
    tenant_id = get_tenant_id()
    red = await svc.red_voucher(
        tenant_id=tenant_id,
        original_voucher_no=original_voucher_no,
        new_voucher_no=req.new_voucher_no,
        period=req.period,
        user_id=req.user_id,
    )
    await session.commit()
    return GLVoucherResponse(
        voucher_id=red.gl_voucher_id,
        voucher_no=red.voucher_no,
        voucher_date=red.voucher_date,
        summary=red.summary,
        period=red.period,
        is_period_closed=red.is_period_closed,
        red_original_voucher_no=red.red_original_voucher_no,
        business_ref_type=red.business_ref_type,
        business_ref_id=red.business_ref_id,
        created_at=red.created_at,
    )


@router.post("/period-close")
@require_permission("fin:accounting:period-close")
async def period_close(
    req: PeriodCloseRequest,
    svc: AccountingService = Depends(get_accounting_service),
    session: AsyncSession = Depends(get_db_session),
) -> PeriodCloseResponse:
    tenant_id = get_tenant_id()
    closed_count = await svc.period_close(
        tenant_id=tenant_id,
        period=req.period,
        user_id=req.user_id,
    )
    await session.commit()
    return PeriodCloseResponse(period=req.period, closed_voucher_count=closed_count)


@router.get("/reports/{report_type}")
@require_permission("fin:accounting:report-read")
async def get_financial_report(
    report_type: str,
    period: str | None = Query(None),
    svc: AccountingService = Depends(get_accounting_service),
) -> FinancialReportResponse:
    tenant_id = get_tenant_id()
    data = await svc.get_financial_report(
        tenant_id=tenant_id,
        report_type=report_type,
        period=period,
    )
    return FinancialReportResponse(report_type=report_type, data=data)