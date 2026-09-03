"""FIN 测试共享基础设施 - SecurityContext、测试用 FastAPI app、MockSession。

为 API 集成测试提供：
- autouse SecurityContext（tenant_admin，全权限放行）
- MockSession（AsyncSession 轻量 mock）
- create_fin_app() 工厂（挂载 fin_routes + FINError → HTTP 状态码映射）
- fin_app_factory fixture
- 真实 aggregate 构建辅助
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.fin.aggregates.ap_voucher_aggregate import APVoucherAggregate
from app.domain.fin.aggregates.ar_voucher_aggregate import ARVoucherAggregate
from app.domain.fin.aggregates.gl_account_aggregate import GLAccountAggregate
from app.domain.fin.aggregates.gl_voucher_aggregate import GLVoucherAggregate
from app.domain.fin.aggregates.invoice_aggregate import InvoiceAggregate, InvoiceLine
from app.domain.fin.aggregates.payment_aggregate import PaymentAggregate
from app.domain.fin.aggregates.settlement_aggregate import SettlementAggregate, SettlementLine
from app.domain.fin.aggregates.treasury_account_aggregate import TreasuryAccountAggregate
from app.domain.fin.aggregates.treasury_transfer_aggregate import TreasuryTransferAggregate
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import (
    GLAccountCategory,
    BalanceDirection,
    InvoiceType,
    PaymentMethod,
    SettlementType,
    TreasuryAccountType,
)
from app.domain.fin.value_objects.money import Money
from app.interfaces.api.v1.fin.routes import fin_routes
from app.interfaces.api.v1.fin.routes._deps import (
    get_accounting_service,
    get_db_session,
    get_invoice_service,
    get_payment_service,
    get_receipt_service,
    get_reconciliation_service,
    get_settlement_service,
    get_treasury_service,
)
from app.interfaces.middleware.error_handler import (
    FINErrorCode as MiddlewareFINErrorCode,
    _status_for_fin_code,
)
from app.interfaces.middleware.security_context import (
    PermissionSummary,
    ResolvedDataScope,
    SecurityContext,
    TenantIdentity,
    UserIdentity,
)

TENANT_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")
USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000002")
API_PREFIX = "/api/v1"


# --------------------------------------------------------------------------- #
# SecurityContext                                                             #
# --------------------------------------------------------------------------- #

def make_security_context(
    *,
    is_tenant_admin: bool = True,
    is_platform_admin: bool = False,
    permissions: frozenset[str] = frozenset(),
) -> SecurityContext:
    """构建测试用 SecurityContext。"""
    return SecurityContext(
        user=UserIdentity(
            user_id=USER_ID,
            username="fin-tester",
            is_tenant_admin=is_tenant_admin,
            is_platform_admin=is_platform_admin,
        ),
        tenant=TenantIdentity(tenant_id=TENANT_ID),
        roles=(),
        permissions=PermissionSummary(codes=permissions),
        data_scope=ResolvedDataScope(),
    )


@pytest.fixture(autouse=True)
def _fin_security_context() -> Any:
    """为所有 fin 测试注入 tenant_admin 安全上下文（全权限放行）。"""
    token = SecurityContext.set(make_security_context())
    yield
    SecurityContext.reset(token)


# --------------------------------------------------------------------------- #
# MockSession                                                                 #
# --------------------------------------------------------------------------- #

class MockSession:
    """AsyncSession 轻量 mock - 仅满足路由对 session.commit() 的依赖。"""

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def close(self) -> None:
        return None


# --------------------------------------------------------------------------- #
# FastAPI app 工厂                                                            #
# --------------------------------------------------------------------------- #

def create_fin_app(deps_overrides: dict[Any, Callable] | None = None) -> FastAPI:
    """创建挂载 fin_routes 的测试 app，注册 FINError → HTTP 状态码处理器。

    domain FINError 经 error_handler 中间件 FINErrorCode(value) 转换后，
    由 _status_for_fin_code 映射到正确 HTTP 状态码，验证完整错误处理链。
    """
    app = FastAPI()
    app.include_router(fin_routes, prefix=API_PREFIX)

    @app.exception_handler(FINError)
    async def _fin_error_handler(request: Request, exc: FINError) -> JSONResponse:
        mw_code = MiddlewareFINErrorCode(exc.code.value)
        status = _status_for_fin_code(mw_code)
        return JSONResponse(
            status_code=status,
            content={
                "error_code": exc.code.value,
                "message": exc.message,
                "details": exc.details,
            },
        )

    app.dependency_overrides[get_db_session] = lambda: MockSession()
    if deps_overrides:
        for dep, impl in deps_overrides.items():
            app.dependency_overrides[dep] = impl
    return app


@pytest.fixture
def fin_app_factory() -> Callable[..., FastAPI]:
    """返回 create_fin_app 工厂，测试按需注入 service override。"""
    return create_fin_app


def make_client(app: FastAPI) -> httpx.AsyncClient:
    """基于 ASGITransport 构建 httpx AsyncClient。"""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test-server")


# --------------------------------------------------------------------------- #
# Mock service 辅助                                                           #
# --------------------------------------------------------------------------- #

def mock_service(**methods: Any) -> MagicMock:
    """构建 mock service：关键字参数方法名→返回值或 side_effect。

    若值是 Exception 实例，设为 side_effect；否则设为 return_value。
    """
    svc = MagicMock()
    for name, ret in methods.items():
        m = AsyncMock()
        if isinstance(ret, BaseException):
            m.side_effect = ret
        else:
            m.return_value = ret
        setattr(svc, name, m)
    return svc


def mock_repo(**methods: Any) -> MagicMock:
    """构建 mock repository（同 mock_service 语义）。"""
    return mock_service(**methods)


# --------------------------------------------------------------------------- #
# 真实 aggregate 构建辅助                                                      #
# --------------------------------------------------------------------------- #

def make_settlement_line(
    line_no: int = 1,
    qty: Decimal = Decimal("10"),
    exclusive: Decimal = Decimal("100.00"),
    inclusive: Decimal = Decimal("113.00"),
    tax_rate: Decimal = Decimal("0.13"),
) -> SettlementLine:
    return SettlementLine(
        line_no=line_no,
        product_id="P-001",
        quantity=qty,
        tax_exclusive_unit_price=Money(exclusive),
        tax_inclusive_unit_price=Money(inclusive),
        tax_rate=tax_rate,
    )


def make_settlement(settlement_no: str = "ST-001") -> SettlementAggregate:
    return SettlementAggregate.create(
        settlement_no=settlement_no,
        settlement_type=SettlementType.PURCHASE,
        counterparty_id="CP-001",
        counterparty_type="SUPPLIER",
        lines=[make_settlement_line()],
        currency="CNY",
        tenant_id=TENANT_ID,
    )


def make_payment(payment_no: str = "PAY-001") -> PaymentAggregate:
    return PaymentAggregate.create(
        payment_no=payment_no,
        ap_voucher_no="AP-001",
        payment_amount=Money(Decimal("1000.00")),
        payment_method=PaymentMethod.BANK_TRANSFER,
        payment_account="BANK-001",
        payee_account="BANK-002",
        tenant_id=TENANT_ID,
    )


def make_invoice_line(
    line_no: int = 1,
    exclusive: Decimal = Decimal("100.00"),
    tax: Decimal = Decimal("13.00"),
    inclusive: Decimal = Decimal("113.00"),
) -> InvoiceLine:
    return InvoiceLine(
        line_no=line_no,
        product_id="P-001",
        product_name="商品A",
        quantity=Decimal("1"),
        tax_exclusive_amount=Money(exclusive),
        tax_amount=Money(tax),
        tax_inclusive_amount=Money(inclusive),
    )


def make_invoice(invoice_no: str = "INV-001") -> InvoiceAggregate:
    return InvoiceAggregate.create(
        invoice_code="CODE-001",
        invoice_no=invoice_no,
        invoice_type=InvoiceType.VAT_NORMAL,
        buyer_info={"name": "买方"},
        seller_info={"name": "卖方"},
        lines=[make_invoice_line()],
        tenant_id=TENANT_ID,
    )


def make_ar_voucher(voucher_no: str = "AR-001") -> ARVoucherAggregate:
    return ARVoucherAggregate.create(
        voucher_no=voucher_no,
        business_ref_type="SETTLEMENT",
        business_ref_id="ST-001",
        receivable_amount=Money(Decimal("1000.00")),
        tenant_id=TENANT_ID,
    )


def make_ap_voucher(voucher_no: str = "AP-001") -> APVoucherAggregate:
    return APVoucherAggregate.create(
        voucher_no=voucher_no,
        business_ref_type="SETTLEMENT",
        business_ref_id="ST-001",
        payable_amount=Money(Decimal("1000.00")),
        tenant_id=TENANT_ID,
    )


def make_gl_account(account_code: str = "1001") -> GLAccountAggregate:
    return GLAccountAggregate.create(
        account_code=account_code,
        account_name="库存现金",
        category=GLAccountCategory.ASSET,
        balance_direction=BalanceDirection.DEBIT,
        tenant_id=TENANT_ID,
    )


def make_treasury_account(account_no: str = "BANK-001") -> TreasuryAccountAggregate:
    return TreasuryAccountAggregate.create(
        account_no=account_no,
        account_type=TreasuryAccountType.BANK,
        currency="CNY",
        opening_balance=Money(Decimal("10000.00")),
        tenant_id=TENANT_ID,
    )


def make_treasury_transfer(transfer_no: str = "TF-001") -> TreasuryTransferAggregate:
    return TreasuryTransferAggregate.create(
        transfer_no=transfer_no,
        from_account_id=uuid4(),
        to_account_id=uuid4(),
        transfer_amount=Money(Decimal("500.00")),
        reason="调拨",
        tenant_id=TENANT_ID,
    )