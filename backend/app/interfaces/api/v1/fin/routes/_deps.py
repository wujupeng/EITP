"""FIN 路由共享依赖 - 安全上下文与服务工厂。"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.fin.accounting_service import AccountingService
from app.application.fin.invoice_service import InvoiceService
from app.application.fin.payment_service import PaymentService
from app.application.fin.receipt_service import ReceiptService
from app.application.fin.reconciliation_service import ReconciliationService
from app.application.fin.settlement_service import SettlementService
from app.application.fin.treasury_service import TreasuryService
from app.infrastructure.fin.ap_voucher_repository import APVoucherRepository
from app.infrastructure.fin.ar_voucher_repository import ARVoucherRepository
from app.infrastructure.fin.bank_ref_client import BankRefClient
from app.infrastructure.fin.collection_task_repository import (
    CollectionTaskRepository,
)
from app.infrastructure.fin.gl_account_repository import GLAccountRepository
from app.infrastructure.fin.gl_voucher_repository import GLVoucherRepository
from app.infrastructure.fin.invoice_archive_repository import (
    InvoiceArchiveRepository,
)
from app.infrastructure.fin.invoice_repository import InvoiceRepository
from app.infrastructure.fin.payment_repository import PaymentRepository
from app.infrastructure.fin.pur_order_read_view import PurOrderReadView
from app.infrastructure.fin.receipt_repository import ReceiptRepository
from app.infrastructure.fin.reconciliation_repository import (
    ReconciliationRepository,
)
from app.infrastructure.fin.sal_order_read_view import SalOrderReadView
from app.infrastructure.fin.settlement_repository import SettlementRepository
from app.infrastructure.fin.treasury_account_repository import (
    TreasuryAccountRepository,
)
from app.infrastructure.fin.treasury_transfer_repository import (
    TreasuryTransferRepository,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.security_context import SecurityContext


def get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    tenant_id = ctx.tenant.tenant_id if ctx else None
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)
    return tenant_id


def get_user_id() -> str:
    ctx = SecurityContext.current()
    if ctx and ctx.user:
        return str(ctx.user.user_id)
    return ""


def get_settlement_service(
    session: AsyncSession = Depends(get_db_session),
) -> SettlementService:
    return SettlementService(
        settlement_repo=SettlementRepository(session),
        ar_repo=ARVoucherRepository(session),
        ap_repo=APVoucherRepository(session),
        pur_read_view=PurOrderReadView(session),
        sal_read_view=SalOrderReadView(session),
    )


def get_payment_service(
    session: AsyncSession = Depends(get_db_session),
) -> PaymentService:
    return PaymentService(
        payment_repo=PaymentRepository(session),
        ap_repo=APVoucherRepository(session),
        bank_ref_client=BankRefClient(session),
    )


def get_receipt_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReceiptService:
    return ReceiptService(
        receipt_repo=ReceiptRepository(session),
        ar_repo=ARVoucherRepository(session),
        collection_task_repo=CollectionTaskRepository(session),
    )


def get_invoice_service(
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceService:
    return InvoiceService(
        invoice_repo=InvoiceRepository(session),
        archive_repo=InvoiceArchiveRepository(session),
    )


def get_reconciliation_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReconciliationService:
    return ReconciliationService(
        recon_repo=ReconciliationRepository(session),
    )


def get_accounting_service(
    session: AsyncSession = Depends(get_db_session),
) -> AccountingService:
    return AccountingService(
        ar_repo=ARVoucherRepository(session),
        ap_repo=APVoucherRepository(session),
        gl_account_repo=GLAccountRepository(session),
        gl_voucher_repo=GLVoucherRepository(session),
    )


def get_treasury_service(
    session: AsyncSession = Depends(get_db_session),
) -> TreasuryService:
    return TreasuryService(
        account_repo=TreasuryAccountRepository(session),
        transfer_repo=TreasuryTransferRepository(session),
    )