"""FIN 资金中心应用服务 - TreasuryService。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.fin.aggregates.treasury_account_aggregate import (
    TreasuryAccountAggregate,
)
from app.domain.fin.aggregates.treasury_transfer_aggregate import (
    TreasuryTransferAggregate,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import TreasuryAccountType
from app.domain.fin.value_objects.money import Money
from app.infrastructure.fin.treasury_account_repository import (
    TreasuryAccountRepository,
)
from app.infrastructure.fin.treasury_transfer_repository import (
    TreasuryTransferRepository,
)

logger = get_logger(__name__)


class TreasuryService:
    """资金中心应用服务 - 账户/调拨/冻结/现金流预测。"""

    def __init__(
        self,
        account_repo: TreasuryAccountRepository,
        transfer_repo: TreasuryTransferRepository,
    ) -> None:
        self._account_repo = account_repo
        self._transfer_repo = transfer_repo

    async def create_treasury_account(
        self,
        tenant_id: UUID,
        account_no: str,
        account_type: str,
        currency: str,
        opening_balance: Decimal,
    ) -> TreasuryAccountAggregate:
        existing = await self._account_repo.get_by_no(account_no)
        if existing is not None:
            raise FINError(
                FINErrorCode.TREASURY_ACCOUNT_DUPLICATE,
                f"treasury account {account_no} already exists",
            )
        account = TreasuryAccountAggregate.create(
            account_no=account_no,
            account_type=TreasuryAccountType(account_type),
            currency=currency,
            opening_balance=Money(opening_balance, currency),
            tenant_id=tenant_id,
        )
        await self._account_repo.save(account)
        logger.info("treasury_account_created", account_no=account_no)
        return account

    async def list_treasury_accounts(
        self,
        tenant_id: UUID,
        account_type: str | None = None,
        currency: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        accounts = await self._account_repo.list_treasury_accounts(
            tenant_id,
            account_type=account_type,
            currency=currency,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "account_id": str(a.account_id),
                "account_no": a.account_no,
                "account_type": a.account_type.value,
                "currency": a.currency,
                "balance": str(a.balance.amount),
                "frozen_amount": str(a.frozen_amount.amount),
                "available_balance": str(a.available_balance().amount),
            }
            for a in accounts
        ]

    async def get_account_balance(
        self, tenant_id: UUID, account_no: str
    ) -> dict[str, Any]:
        account = await self._account_repo.get_by_no(account_no)
        if account is None:
            raise FINError(
                FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND,
                f"treasury account {account_no} not found",
            )
        return {
            "account_no": account.account_no,
            "currency": account.currency,
            "balance": str(account.balance.amount),
            "frozen_amount": str(account.frozen_amount.amount),
            "available_balance": str(account.available_balance().amount),
        }

    async def request_treasury_transfer(
        self,
        tenant_id: UUID,
        transfer_no: str,
        from_account_id: UUID,
        to_account_id: UUID,
        transfer_amount: Decimal,
        reason: str,
        currency: str = "CNY",
    ) -> TreasuryTransferAggregate:
        existing = await self._transfer_repo.get_by_no(transfer_no)
        if existing is not None:
            raise FINError(
                FINErrorCode.TREASURY_TRANSFER_FAILED,
                f"transfer {transfer_no} already exists",
            )
        from_account = await self._account_repo.get_by_id(from_account_id)
        if from_account is None:
            raise FINError(
                FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND,
                f"from account {from_account_id} not found",
            )
        amount = Money(transfer_amount, currency)
        if amount > from_account.available_balance():
            raise FINError(
                FINErrorCode.TREASURY_INSUFFICIENT_BALANCE,
                f"transfer {amount} exceeds available {from_account.available_balance()}",
            )
        transfer = TreasuryTransferAggregate.create(
            transfer_no=transfer_no,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            transfer_amount=amount,
            reason=reason,
            tenant_id=tenant_id,
        )
        await self._transfer_repo.save(transfer)
        logger.info("treasury_transfer_requested", transfer_no=transfer_no)
        return transfer

    async def approve_treasury_transfer(
        self,
        tenant_id: UUID,
        transfer_no: str,
        approver_id: str,
    ) -> TreasuryTransferAggregate:
        transfer = await self._transfer_repo.get_by_no(transfer_no)
        if transfer is None:
            raise FINError(
                FINErrorCode.TREASURY_TRANSFER_NOT_FOUND,
                f"transfer {transfer_no} not found",
            )
        approved = transfer.approve(approver_id)
        await self._transfer_repo.save(approved)
        logger.info(
            "treasury_transfer_approved",
            transfer_no=transfer_no,
            approver_id=approver_id,
        )
        return approved

    async def execute_treasury_transfer(
        self, tenant_id: UUID, transfer_no: str
    ) -> TreasuryTransferAggregate:
        transfer = await self._transfer_repo.get_by_no(transfer_no)
        if transfer is None:
            raise FINError(
                FINErrorCode.TREASURY_TRANSFER_NOT_FOUND,
                f"transfer {transfer_no} not found",
            )
        executing = transfer.execute()
        await self._transfer_repo.save(executing)
        from_account = await self._account_repo.get_by_id(transfer.from_account_id)
        to_account = await self._account_repo.get_by_id(transfer.to_account_id)
        if from_account is None or to_account is None:
            raise FINError(
                FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND,
                f"transfer {transfer_no} account not found",
            )
        withdrawn = from_account.withdraw(transfer.transfer_amount)
        deposited = to_account.deposit(transfer.transfer_amount)
        await self._account_repo.save(withdrawn)
        await self._account_repo.save(deposited)
        succeeded = executing.transfer_success()
        await self._transfer_repo.save(succeeded)
        logger.info("treasury_transfer_executed", transfer_no=transfer_no)
        return succeeded

    async def freeze_account(
        self, tenant_id: UUID, account_no: str, amount: Decimal, currency: str = "CNY"
    ) -> TreasuryAccountAggregate:
        account = await self._account_repo.get_by_no(account_no)
        if account is None:
            raise FINError(
                FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND,
                f"treasury account {account_no} not found",
            )
        frozen = account.freeze(Money(amount, currency))
        await self._account_repo.save(frozen)
        logger.info("treasury_account_frozen", account_no=account_no, amount=str(amount))
        return frozen

    async def unfreeze_account(
        self, tenant_id: UUID, account_no: str, amount: Decimal, currency: str = "CNY"
    ) -> TreasuryAccountAggregate:
        account = await self._account_repo.get_by_no(account_no)
        if account is None:
            raise FINError(
                FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND,
                f"treasury account {account_no} not found",
            )
        unfrozen = account.unfreeze(Money(amount, currency))
        await self._account_repo.save(unfrozen)
        logger.info("treasury_account_unfrozen", account_no=account_no, amount=str(amount))
        return unfrozen

    async def get_cash_flow_forecast(
        self,
        tenant_id: UUID,
        forecast_days: int = 30,
    ) -> dict[str, Any]:
        accounts = await self._account_repo.list_treasury_accounts(
            tenant_id, limit=10000, offset=0
        )
        transfers = await self._transfer_repo.list_transfers(
            tenant_id, status="PENDING_APPROVAL", limit=10000, offset=0
        )
        total_balance = Decimal("0")
        total_frozen = Decimal("0")
        total_available = Decimal("0")
        for a in accounts:
            total_balance += a.balance.amount
            total_frozen += a.frozen_amount.amount
            total_available += a.available_balance().amount
        pending_outflow = Decimal("0")
        for t in transfers:
            pending_outflow += t.transfer_amount.amount
        forecast_date = date.today() + timedelta(days=forecast_days)
        return {
            "forecast_date": forecast_date.isoformat(),
            "forecast_days": forecast_days,
            "total_balance": str(total_balance),
            "total_frozen": str(total_frozen),
            "total_available": str(total_available),
            "pending_outflow": str(pending_outflow),
            "projected_available": str(total_available - pending_outflow),
            "account_count": len(accounts),
        }