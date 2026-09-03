"""FIN 资金中心路由 - 7 个接口。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.fin.treasury_service import TreasuryService
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.infrastructure.db.session import get_db_session
from app.interfaces.api.v1.fin.routes._deps import (
    get_tenant_id,
    get_treasury_service,
)
from app.interfaces.api.v1.fin.schemas.treasury_schemas import (
    TreasuryAccountBalanceResponse,
    TreasuryAccountCreateRequest,
    TreasuryAccountFreezeRequest,
    TreasuryAccountListQuery,
    TreasuryAccountResponse,
    TreasuryForecastQuery,
    TreasuryForecastResponse,
    TreasuryTransferApproveRequest,
    TreasuryTransferCreateRequest,
    TreasuryTransferResponse,
)
from app.interfaces.middleware.permission_interceptor import require_permission

router = APIRouter(prefix="/treasury", tags=["EITP-FIN-001 Treasury"])


def _to_account_response(account) -> TreasuryAccountResponse:
    return TreasuryAccountResponse(
        account_id=account.account_id,
        account_no=account.account_no,
        account_type=account.account_type.value,
        currency=account.currency,
        balance=account.balance.amount,
        frozen_amount=account.frozen_amount.amount,
        available_balance=account.available_balance().amount,
    )


def _to_transfer_response(transfer) -> TreasuryTransferResponse:
    return TreasuryTransferResponse(
        transfer_id=transfer.transfer_id,
        transfer_no=transfer.transfer_no,
        from_account_id=transfer.from_account_id,
        to_account_id=transfer.to_account_id,
        transfer_amount=transfer.transfer_amount.amount,
        currency=transfer.transfer_amount.currency,
        reason=transfer.reason,
        status=transfer.status.value,
        approver_ids=list(transfer.approver_ids),
        created_at=transfer.created_at,
        updated_at=transfer.updated_at,
    )


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
@require_permission("fin:treasury:account-create")
async def create_treasury_account(
    req: TreasuryAccountCreateRequest,
    svc: TreasuryService = Depends(get_treasury_service),
    session: AsyncSession = Depends(get_db_session),
) -> TreasuryAccountResponse:
    tenant_id = get_tenant_id()
    account = await svc.create_treasury_account(
        tenant_id=tenant_id,
        account_no=req.account_no,
        account_type=req.account_type,
        currency=req.currency,
        opening_balance=req.opening_balance,
    )
    await session.commit()
    return _to_account_response(account)


@router.get("/accounts")
@require_permission("fin:treasury:account-read")
async def list_treasury_accounts(
    query: TreasuryAccountListQuery = Depends(),
    svc: TreasuryService = Depends(get_treasury_service),
) -> list[TreasuryAccountResponse]:
    tenant_id = get_tenant_id()
    items = await svc.list_treasury_accounts(
        tenant_id,
        account_type=query.account_type,
        currency=query.currency,
        limit=query.limit,
        offset=query.offset,
    )
    return [TreasuryAccountResponse(**item) for item in items]


@router.get("/accounts/{account_id}/balance")
@require_permission("fin:treasury:account-read")
async def get_account_balance(
    account_id: UUID,
    svc: TreasuryService = Depends(get_treasury_service),
) -> TreasuryAccountBalanceResponse:
    account = await svc._account_repo.get_by_id(account_id)
    if account is None:
        raise FINError(
            FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND,
            f"treasury account {account_id} not found",
        )
    balance = await svc.get_account_balance(account.tenant_id, account.account_no)
    return TreasuryAccountBalanceResponse(**balance)


@router.post("/transfers", status_code=status.HTTP_201_CREATED)
@require_permission("fin:treasury:transfer-request")
async def request_treasury_transfer(
    req: TreasuryTransferCreateRequest,
    svc: TreasuryService = Depends(get_treasury_service),
    session: AsyncSession = Depends(get_db_session),
) -> TreasuryTransferResponse:
    tenant_id = get_tenant_id()
    transfer = await svc.request_treasury_transfer(
        tenant_id=tenant_id,
        transfer_no=req.transfer_no,
        from_account_id=req.from_account_id,
        to_account_id=req.to_account_id,
        transfer_amount=req.transfer_amount,
        reason=req.reason,
        currency=req.currency,
    )
    await session.commit()
    return _to_transfer_response(transfer)


@router.post("/transfers/{transfer_no}/approve")
@require_permission("fin:treasury:transfer-approve")
async def approve_treasury_transfer(
    transfer_no: str,
    req: TreasuryTransferApproveRequest,
    svc: TreasuryService = Depends(get_treasury_service),
    session: AsyncSession = Depends(get_db_session),
) -> TreasuryTransferResponse:
    tenant_id = get_tenant_id()
    approved = await svc.approve_treasury_transfer(
        tenant_id=tenant_id,
        transfer_no=transfer_no,
        approver_id=req.approver_id,
    )
    await session.commit()
    return _to_transfer_response(approved)


@router.post("/accounts/{account_id}/freeze")
@require_permission("fin:treasury:account-freeze")
async def freeze_account(
    account_id: UUID,
    req: TreasuryAccountFreezeRequest,
    svc: TreasuryService = Depends(get_treasury_service),
    session: AsyncSession = Depends(get_db_session),
) -> TreasuryAccountResponse:
    account = await svc._account_repo.get_by_id(account_id)
    if account is None:
        raise FINError(
            FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND,
            f"treasury account {account_id} not found",
        )
    frozen = await svc.freeze_account(
        tenant_id=account.tenant_id,
        account_no=account.account_no,
        amount=req.amount,
        currency=req.currency,
    )
    await session.commit()
    return _to_account_response(frozen)


@router.get("/forecast")
@require_permission("fin:treasury:forecast-read")
async def get_cash_flow_forecast(
    query: TreasuryForecastQuery = Depends(),
    svc: TreasuryService = Depends(get_treasury_service),
) -> TreasuryForecastResponse:
    tenant_id = get_tenant_id()
    result = await svc.get_cash_flow_forecast(
        tenant_id=tenant_id,
        forecast_days=query.forecast_days,
    )
    return TreasuryForecastResponse(**result)