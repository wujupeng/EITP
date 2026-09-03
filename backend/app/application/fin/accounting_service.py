"""FIN 会计核算应用服务 - AccountingService。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.fin.aggregates.gl_account_aggregate import GLAccountAggregate
from app.domain.fin.aggregates.gl_voucher_aggregate import (
    GLVoucherAggregate,
    GLVoucherLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import (
    AgingBucket,
    BalanceDirection,
    GLAccountCategory,
)
from app.domain.fin.value_objects.money import Money
from app.infrastructure.fin.ap_voucher_repository import APVoucherRepository
from app.infrastructure.fin.ar_voucher_repository import ARVoucherRepository
from app.infrastructure.fin.gl_account_repository import GLAccountRepository
from app.infrastructure.fin.gl_voucher_repository import GLVoucherRepository

logger = get_logger(__name__)

FIN_MANAGER_ROLE = "FIN_MANAGER"

_AGING_RANGES: list[tuple[AgingBucket, int, int]] = [
    (AgingBucket.B_0_30, 0, 30),
    (AgingBucket.B_31_60, 31, 60),
    (AgingBucket.B_61_90, 61, 90),
    (AgingBucket.B_91_180, 91, 180),
    (AgingBucket.B_180_PLUS, 181, 999999),
]


def _aging_bucket(days: int) -> AgingBucket:
    for bucket, low, high in _AGING_RANGES:
        if low <= days <= high:
            return bucket
    return AgingBucket.B_180_PLUS


class AccountingService:
    """会计核算应用服务 - AR/AP 查询 + 账龄分析 + 总账 + 红冲 + 期末结账 + 财务报表。"""

    def __init__(
        self,
        ar_repo: ARVoucherRepository,
        ap_repo: APVoucherRepository,
        gl_account_repo: GLAccountRepository,
        gl_voucher_repo: GLVoucherRepository,
        role_checker: object | None = None,
    ) -> None:
        self._ar_repo = ar_repo
        self._ap_repo = ap_repo
        self._gl_account_repo = gl_account_repo
        self._gl_voucher_repo = gl_voucher_repo
        self._role_checker = role_checker

    async def _check_fin_manager_role(self, user_id: str) -> None:
        if self._role_checker is None:
            return
        roles = await self._role_checker.get_user_roles(user_id)
        if FIN_MANAGER_ROLE not in roles:
            raise FINError(
                FINErrorCode.PAYMENT_APPROVAL_EXCEED_AUTHORITY,
                f"user {user_id} lacks role {FIN_MANAGER_ROLE}",
            )

    async def list_ar_vouchers(
        self,
        tenant_id: UUID,
        status: str | None = None,
        is_overdue: bool | None = None,
        business_ref_type: str | None = None,
        business_ref_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        vouchers = await self._ar_repo.list_ar_vouchers(
            tenant_id,
            status=status,
            is_overdue=is_overdue,
            business_ref_type=business_ref_type,
            business_ref_id=business_ref_id,
            limit=limit,
            offset=offset,
        )
        today = date.today()
        result: list[dict[str, Any]] = []
        for v in vouchers:
            aging_days = (
                (today - v.due_date).days if v.due_date is not None else 0
            )
            result.append(
                {
                    "voucher_id": str(v.voucher_id),
                    "voucher_no": v.voucher_no,
                    "business_ref_type": v.business_ref_type,
                    "business_ref_id": v.business_ref_id,
                    "receivable_amount": str(v.receivable_amount.amount),
                    "received_amount": str(v.received_amount.amount),
                    "unreceived_amount": str(v.unreceived_amount.amount),
                    "status": v.status.value,
                    "credit_period_days": v.credit_period_days,
                    "due_date": v.due_date.isoformat() if v.due_date else None,
                    "is_overdue": v.is_overdue,
                    "overdue_days": v.overdue_days,
                    "aging_days": aging_days,
                    "aging_bucket": _aging_bucket(aging_days).value,
                }
            )
        return result

    async def list_ap_vouchers(
        self,
        tenant_id: UUID,
        status: str | None = None,
        is_overdue: bool | None = None,
        business_ref_type: str | None = None,
        business_ref_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        vouchers = await self._ap_repo.list_ap_vouchers(
            tenant_id,
            status=status,
            is_overdue=is_overdue,
            business_ref_type=business_ref_type,
            business_ref_id=business_ref_id,
            limit=limit,
            offset=offset,
        )
        today = date.today()
        result: list[dict[str, Any]] = []
        for v in vouchers:
            aging_days = (
                (today - v.due_date).days if v.due_date is not None else 0
            )
            result.append(
                {
                    "voucher_id": str(v.voucher_id),
                    "voucher_no": v.voucher_no,
                    "business_ref_type": v.business_ref_type,
                    "business_ref_id": v.business_ref_id,
                    "payable_amount": str(v.payable_amount.amount),
                    "paid_amount": str(v.paid_amount.amount),
                    "unpaid_amount": str(v.unpaid_amount.amount),
                    "status": v.status.value,
                    "payment_terms": v.payment_terms,
                    "due_date": v.due_date.isoformat() if v.due_date else None,
                    "is_overdue": v.is_overdue,
                    "overdue_days": v.overdue_days,
                    "aging_days": aging_days,
                    "aging_bucket": _aging_bucket(aging_days).value,
                }
            )
        return result

    async def get_aging_analysis(
        self,
        tenant_id: UUID,
        as_of_date: date | None = None,
    ) -> dict[str, Any]:
        ref_date = as_of_date or date.today()
        ar_vouchers = await self._ar_repo.list_ar_vouchers(
            tenant_id, limit=10000, offset=0
        )
        ap_vouchers = await self._ap_repo.list_ap_vouchers(
            tenant_id, limit=10000, offset=0
        )
        ar_buckets: dict[str, Decimal] = {b.value: Decimal("0") for b in AgingBucket}
        ap_buckets: dict[str, Decimal] = {b.value: Decimal("0") for b in AgingBucket}
        for v in ar_vouchers:
            days = (ref_date - v.due_date).days if v.due_date else 0
            bucket = _aging_bucket(days)
            ar_buckets[bucket.value] += v.unreceived_amount.amount
        for v in ap_vouchers:
            days = (ref_date - v.due_date).days if v.due_date else 0
            bucket = _aging_bucket(days)
            ap_buckets[bucket.value] += v.unpaid_amount.amount
        return {
            "as_of_date": ref_date.isoformat(),
            "ar_aging": {
                b.value: str(ar_buckets[b.value]) for b in AgingBucket
            },
            "ar_total_unreceived": str(sum(ar_buckets.values())),
            "ap_aging": {
                b.value: str(ap_buckets[b.value]) for b in AgingBucket
            },
            "ap_total_unpaid": str(sum(ap_buckets.values())),
        }

    async def create_gl_account(
        self,
        tenant_id: UUID,
        account_code: str,
        account_name: str,
        category: str,
        balance_direction: str,
        parent_code: str | None = None,
        opening_balance: Decimal | None = None,
    ) -> GLAccountAggregate:
        existing = await self._gl_account_repo.get_by_code(tenant_id, account_code)
        if existing is not None:
            raise FINError(
                FINErrorCode.GL_ACCOUNT_DUPLICATE,
                f"account code {account_code} already exists",
            )
        account = GLAccountAggregate.create(
            account_code=account_code,
            account_name=account_name,
            category=GLAccountCategory(category),
            balance_direction=BalanceDirection(balance_direction),
            tenant_id=tenant_id,
            parent_code=parent_code,
            opening_balance=opening_balance,
        )
        await self._gl_account_repo.save(account)
        logger.info(
            "gl_account_created",
            account_code=account_code,
            category=category,
        )
        return account

    async def list_gl_accounts(
        self,
        tenant_id: UUID,
        category: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        accounts = await self._gl_account_repo.list_gl_accounts(
            tenant_id, category=category, limit=limit, offset=offset
        )
        return [
            {
                "account_id": str(a.account_id),
                "account_code": a.account_code,
                "account_name": a.account_name,
                "category": a.category.value,
                "balance_direction": a.balance_direction.value,
                "parent_code": a.parent_code,
                "opening_balance": str(a.opening_balance),
                "period_debit": str(a.period_debit),
                "period_credit": str(a.period_credit),
                "closing_balance": str(a.closing_balance),
            }
            for a in accounts
        ]

    async def list_gl_vouchers(
        self,
        tenant_id: UUID,
        period: str | None = None,
        is_period_closed: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        vouchers = await self._gl_voucher_repo.list_gl_vouchers(
            tenant_id,
            period=period,
            is_period_closed=is_period_closed,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "voucher_id": str(v.gl_voucher_id),
                "voucher_no": v.voucher_no,
                "voucher_date": v.voucher_date.isoformat(),
                "summary": v.summary,
                "period": v.period,
                "is_period_closed": v.is_period_closed,
                "red_original_voucher_no": v.red_original_voucher_no,
                "business_ref_type": v.business_ref_type,
                "business_ref_id": v.business_ref_id,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in vouchers
        ]

    async def create_gl_voucher(
        self,
        tenant_id: UUID,
        voucher_no: str,
        voucher_date: date,
        summary: str,
        period: str,
        lines: list[dict[str, Any]],
        business_ref_type: str | None = None,
        business_ref_id: str | None = None,
    ) -> GLVoucherAggregate:
        domain_lines: list[GLVoucherLine] = []
        for idx, ln in enumerate(lines, start=1):
            domain_lines.append(
                GLVoucherLine(
                    line_no=ln.get("line_no", idx),
                    account_code=ln["account_code"],
                    debit_amount=Money(Decimal(str(ln.get("debit_amount", "0")))),
                    credit_amount=Money(Decimal(str(ln.get("credit_amount", "0")))),
                )
            )
        voucher = GLVoucherAggregate.create(
            voucher_no=voucher_no,
            voucher_date=voucher_date,
            summary=summary,
            period=period,
            tenant_id=tenant_id,
            lines=domain_lines,
            business_ref_type=business_ref_type,
            business_ref_id=business_ref_id,
        )
        posted = voucher.post()
        await self._gl_voucher_repo.save(posted)
        logger.info(
            "gl_voucher_created",
            voucher_no=voucher_no,
            period=period,
            lines=len(domain_lines),
        )
        return posted

    async def red_voucher(
        self,
        tenant_id: UUID,
        original_voucher_no: str,
        new_voucher_no: str,
        period: str,
        user_id: str,
    ) -> GLVoucherAggregate:
        await self._check_fin_manager_role(user_id)
        original = await self._gl_voucher_repo.get_by_no(
            tenant_id, original_voucher_no, period
        )
        if original is None:
            raise FINError(
                FINErrorCode.GL_RED_VOUCHER_ORIGINAL_NOT_FOUND,
                f"original voucher {original_voucher_no} in period {period} not found",
            )
        if original.is_period_closed:
            raise FINError(
                FINErrorCode.GL_PERIOD_CLOSED,
                f"period {period} already closed, cannot red voucher",
            )
        red = original.red_voucher(new_voucher_no)
        red_posted = red.post()
        await self._gl_voucher_repo.save(red_posted)
        logger.info(
            "gl_red_voucher_created",
            original_voucher_no=original_voucher_no,
            new_voucher_no=new_voucher_no,
            user_id=user_id,
        )
        return red_posted

    async def period_close(
        self,
        tenant_id: UUID,
        period: str,
        user_id: str,
    ) -> int:
        await self._check_fin_manager_role(user_id)
        vouchers = await self._gl_voucher_repo.list_gl_vouchers(
            tenant_id, period=period, is_period_closed=False, limit=100000, offset=0
        )
        for v in vouchers:
            if not v.is_balanced():
                raise FINError(
                    FINErrorCode.GL_PERIOD_UNBALANCED,
                    f"voucher {v.voucher_no} in period {period} is unbalanced, "
                    f"cannot close period",
                )
        closed_count = await self._gl_voucher_repo.close_period(tenant_id, period)
        accounts = await self._gl_account_repo.list_gl_accounts(
            tenant_id, limit=100000, offset=0
        )
        for account in accounts:
            carried = account.close_period()
            await self._gl_account_repo.save(carried)
        logger.info(
            "gl_period_closed",
            period=period,
            closed_vouchers=closed_count,
            user_id=user_id,
        )
        return closed_count

    async def get_financial_report(
        self,
        tenant_id: UUID,
        report_type: str,
        period: str | None = None,
    ) -> dict[str, Any]:
        if report_type == "balance_sheet":
            return await self._balance_sheet(tenant_id)
        if report_type == "income_statement":
            return await self._income_statement(tenant_id)
        if report_type == "cash_flow":
            return await self._cash_flow(tenant_id, period)
        if report_type == "ar_ap_detail":
            return await self._ar_ap_detail(tenant_id)
        if report_type == "aging":
            return await self.get_aging_analysis(tenant_id)
        raise FINError(
            FINErrorCode.INTERNAL_ERROR,
            f"unknown report type {report_type}",
        )

    async def _balance_sheet(self, tenant_id: UUID) -> dict[str, Any]:
        accounts = await self._gl_account_repo.list_gl_accounts(
            tenant_id, limit=100000, offset=0
        )
        sections: dict[str, Decimal] = {
            GLAccountCategory.ASSET.value: Decimal("0"),
            GLAccountCategory.LIABILITY.value: Decimal("0"),
            GLAccountCategory.EQUITY.value: Decimal("0"),
        }
        details: list[dict[str, Any]] = []
        for a in accounts:
            if a.category.value in sections:
                sections[a.category.value] += a.closing_balance
            details.append(
                {
                    "account_code": a.account_code,
                    "account_name": a.account_name,
                    "category": a.category.value,
                    "closing_balance": str(a.closing_balance),
                }
            )
        assets = sections[GLAccountCategory.ASSET.value]
        liabilities = sections[GLAccountCategory.LIABILITY.value]
        equity = sections[GLAccountCategory.EQUITY.value]
        return {
            "report_type": "balance_sheet",
            "assets": str(assets),
            "liabilities": str(liabilities),
            "equity": str(equity),
            "is_balanced": assets == liabilities + equity,
            "details": details,
        }

    async def _income_statement(self, tenant_id: UUID) -> dict[str, Any]:
        accounts = await self._gl_account_repo.list_gl_accounts(
            tenant_id, limit=100000, offset=0
        )
        revenue = Decimal("0")
        cost = Decimal("0")
        expense = Decimal("0")
        details: list[dict[str, Any]] = []
        for a in accounts:
            if a.category == GLAccountCategory.REVENUE:
                revenue += a.closing_balance
            elif a.category == GLAccountCategory.COST:
                cost += a.closing_balance
            elif a.category == GLAccountCategory.EXPENSE:
                expense += a.closing_balance
            if a.category.value in ("REVENUE", "COST", "EXPENSE"):
                details.append(
                    {
                        "account_code": a.account_code,
                        "account_name": a.account_name,
                        "category": a.category.value,
                        "closing_balance": str(a.closing_balance),
                    }
                )
        profit = revenue - cost - expense
        return {
            "report_type": "income_statement",
            "revenue": str(revenue),
            "cost": str(cost),
            "expense": str(expense),
            "profit": str(profit),
            "details": details,
        }

    async def _cash_flow(
        self, tenant_id: UUID, period: str | None
    ) -> dict[str, Any]:
        vouchers = await self._gl_voucher_repo.list_gl_vouchers(
            tenant_id,
            period=period,
            limit=100000,
            offset=0,
        )
        operating = Decimal("0")
        for v in vouchers:
            for line in v.lines:
                operating += line.debit_amount.amount - line.credit_amount.amount
        return {
            "report_type": "cash_flow",
            "period": period,
            "operating_cash_flow": str(operating),
            "investing_cash_flow": "0",
            "financing_cash_flow": "0",
            "net_cash_flow": str(operating),
        }

    async def _ar_ap_detail(self, tenant_id: UUID) -> dict[str, Any]:
        ar_list = await self.list_ar_vouchers(tenant_id, limit=100000, offset=0)
        ap_list = await self.list_ap_vouchers(tenant_id, limit=100000, offset=0)
        return {
            "report_type": "ar_ap_detail",
            "ar_vouchers": ar_list,
            "ap_vouchers": ap_list,
        }