"""FIN 付款应用服务 - PaymentService。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.fin.aggregates.payment_aggregate import PaymentAggregate
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.policies.payment_approval_policy import PaymentApprovalPolicy
from app.domain.fin.value_objects.enums import PaymentMethod
from app.domain.fin.value_objects.money import Money
from app.infrastructure.fin.ap_voucher_repository import APVoucherRepository
from app.infrastructure.fin.bank_ref_client import BankRefClient
from app.infrastructure.fin.payment_repository import PaymentRepository

logger = get_logger(__name__)


class PaymentService:
    """付款应用服务 - 申请/审批/执行/银行回调/导入对账单。"""

    def __init__(
        self,
        payment_repo: PaymentRepository,
        ap_repo: APVoucherRepository,
        bank_ref_client: BankRefClient,
        role_checker: object | None = None,
    ) -> None:
        self._payment_repo = payment_repo
        self._ap_repo = ap_repo
        self._bank_ref_client = bank_ref_client
        self._role_checker = role_checker

    async def request_payment(
        self,
        tenant_id: UUID,
        payment_no: str,
        ap_voucher_no: str,
        payment_amount: Decimal,
        payment_method: str,
        payment_account: str,
        payee_account: str,
        currency: str = "CNY",
        expected_payment_date: date | None = None,
    ) -> PaymentAggregate:
        existing = await self._payment_repo.get_by_no(payment_no)
        if existing is not None:
            raise FINError(
                FINErrorCode.PAYMENT_DUPLICATE,
                f"payment {payment_no} already exists",
            )
        ap_voucher = await self._ap_repo.get_by_no(ap_voucher_no)
        if ap_voucher is None:
            raise FINError(
                FINErrorCode.VOUCHER_NOT_FOUND,
                f"AP voucher {ap_voucher_no} not found",
            )
        amount = Money(payment_amount, currency)
        if amount > ap_voucher.unpaid_amount:
            raise FINError(
                FINErrorCode.PAYMENT_EXCEED_AP,
                f"payment amount {amount} exceeds unpaid {ap_voucher.unpaid_amount}",
            )
        payment = PaymentAggregate.create(
            payment_no=payment_no,
            ap_voucher_no=ap_voucher_no,
            payment_amount=amount,
            payment_method=PaymentMethod(payment_method),
            payment_account=payment_account,
            payee_account=payee_account,
            tenant_id=tenant_id,
            expected_payment_date=expected_payment_date,
        )
        submitted = payment.submit()
        await self._payment_repo.save(submitted)
        logger.info(
            "payment_requested",
            payment_no=payment_no,
            ap_voucher_no=ap_voucher_no,
            amount=str(amount.amount),
        )
        return submitted

    async def approve_payment(
        self,
        tenant_id: UUID,
        payment_no: str,
        approver_id: str,
        approval_opinion: str | None = None,
    ) -> PaymentAggregate:
        payment = await self._payment_repo.get_by_no(payment_no)
        if payment is None:
            raise FINError(
                FINErrorCode.PAYMENT_NOT_FOUND,
                f"payment {payment_no} not found",
            )
        approver_roles = await self._get_user_roles(approver_id)
        PaymentApprovalPolicy.check_authority(payment.payment_amount, approver_roles)
        approved = payment.approve(approver_id, approval_opinion)
        await self._payment_repo.save(approved)
        logger.info(
            "payment_approved",
            payment_no=payment_no,
            approver_id=approver_id,
        )
        return approved

    async def reject_payment(
        self,
        tenant_id: UUID,
        payment_no: str,
        approver_id: str,
        approval_opinion: str | None = None,
    ) -> PaymentAggregate:
        payment = await self._payment_repo.get_by_no(payment_no)
        if payment is None:
            raise FINError(
                FINErrorCode.PAYMENT_NOT_FOUND,
                f"payment {payment_no} not found",
            )
        rejected = payment.reject(approver_id, approval_opinion)
        await self._payment_repo.save(rejected)
        logger.info("payment_rejected", payment_no=payment_no, approver_id=approver_id)
        return rejected

    async def execute_payment(
        self, tenant_id: UUID, payment_no: str
    ) -> PaymentAggregate:
        payment = await self._payment_repo.get_by_no(payment_no)
        if payment is None:
            raise FINError(
                FINErrorCode.PAYMENT_NOT_FOUND,
                f"payment {payment_no} not found",
            )
        executing = payment.execute()
        await self._payment_repo.save(executing)
        logger.info("payment_executing", payment_no=payment_no)
        return executing

    async def bank_callback(
        self, payment_no: str, callback_payload: dict[str, Any]
    ) -> PaymentAggregate:
        payment = await self._payment_repo.get_by_no(payment_no)
        if payment is None:
            raise FINError(
                FINErrorCode.PAYMENT_NOT_FOUND,
                f"payment {payment_no} not found",
            )
        parsed = await self._bank_ref_client.parse_callback(callback_payload)
        if parsed["success"]:
            if payment.status.value == "SUCCESS":
                raise FINError(
                    FINErrorCode.PAYMENT_ALREADY_SUCCESS,
                    f"payment {payment_no} already success",
                )
            succeeded = payment.bank_callback_success(
                bank_ref=parsed["bank_ref"],
                actual_payment_date=date.today(),
            )
            await self._payment_repo.save(succeeded)
            ap_voucher = await self._ap_repo.get_by_no(payment.ap_voucher_no)
            if ap_voucher is not None:
                updated_ap = ap_voucher.apply_payment(payment.payment_amount)
                await self._ap_repo.save(updated_ap)
            logger.info(
                "payment_success",
                payment_no=payment_no,
                bank_ref=parsed["bank_ref"],
            )
            return succeeded
        failed = payment.bank_callback_failed(parsed.get("status"))
        await self._payment_repo.save(failed)
        logger.info("payment_failed", payment_no=payment_no)
        return failed

    async def import_bank_statements(
        self, tenant_id: UUID, statements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        imported = await self._bank_ref_client.import_bank_statements(tenant_id, statements)
        logger.info(
            "bank_statements_imported",
            tenant_id=str(tenant_id),
            count=len(imported),
        )
        return imported

    async def _get_user_roles(self, user_id: str) -> list[str]:
        if self._role_checker is None:
            return []
        return await self._role_checker.get_user_roles(user_id)