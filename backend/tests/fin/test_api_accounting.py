"""Accounting API 集成测试 - AR/AP 凭证/总账/期间关闭/报表全链路。

覆盖：
- GET  /api/v1/fin/accounting/ar-vouchers AR 凭证列表
- GET  /api/v1/fin/accounting/ap-vouchers AP 凭证列表
- GET  /api/v1/fin/accounting/aging-analysis 账龄分析
- POST /api/v1/fin/accounting/gl-accounts 创建总账科目
- POST /api/v1/fin/accounting/gl-vouchers 创建总账凭证（借贷平衡校验）
- POST /api/v1/fin/accounting/period-close 期间关闭
- GET  /api/v1/fin/accounting/reports/{type} 财务报表
- GL_UNBALANCED → 422, GL_PERIOD_CLOSED → 423
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.fin.aggregates.gl_voucher_aggregate import GLVoucherAggregate, GLVoucherLine
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.money import Money
from app.interfaces.api.v1.fin.routes._deps import get_accounting_service
from tests.fin.conftest import TENANT_ID, make_client, make_gl_account, mock_service


def _ar_voucher_dict(voucher_no: str = "AR-001") -> dict:
    return {
        "voucher_id": str(uuid4()),
        "voucher_no": voucher_no,
        "business_ref_type": "SETTLEMENT",
        "business_ref_id": "ST-001",
        "receivable_amount": "1000.00",
        "received_amount": "300.00",
        "unreceived_amount": "700.00",
        "status": "PARTIAL",
        "credit_period_days": 30,
        "due_date": "2026-09-30",
        "is_overdue": False,
        "overdue_days": 0,
        "aging_days": 5,
        "aging_bucket": "B_0_30",
    }


def _ap_voucher_dict(voucher_no: str = "AP-001") -> dict:
    return {
        "voucher_id": str(uuid4()),
        "voucher_no": voucher_no,
        "business_ref_type": "SETTLEMENT",
        "business_ref_id": "ST-001",
        "payable_amount": "2000.00",
        "paid_amount": "500.00",
        "unpaid_amount": "1500.00",
        "status": "PARTIAL",
        "payment_terms": 30,
        "due_date": "2026-09-30",
        "is_overdue": False,
        "overdue_days": 0,
        "aging_days": 5,
        "aging_bucket": "B_0_30",
    }


def _balanced_gl_voucher(voucher_no: str = "GL-001") -> GLVoucherAggregate:
    return GLVoucherAggregate.create(
        voucher_no=voucher_no,
        voucher_date=date(2026, 9, 1),
        summary="测试凭证",
        period="2026-09",
        tenant_id=TENANT_ID,
        lines=[
            GLVoucherLine(line_no=1, account_code="1001", debit_amount=Money("100.00"), credit_amount=Money("0")),
            GLVoucherLine(line_no=2, account_code="2001", debit_amount=Money("0"), credit_amount=Money("100.00")),
        ],
    )


def _gl_voucher_body(voucher_no: str = "GL-001") -> dict:
    return {
        "voucher_no": voucher_no,
        "voucher_date": "2026-09-01",
        "summary": "测试凭证",
        "period": "2026-09",
        "lines": [
            {"account_code": "1001", "debit_amount": "100.00", "credit_amount": "0.00"},
            {"account_code": "2001", "debit_amount": "0.00", "credit_amount": "100.00"},
        ],
    }


class AccountingApiTest:
    """Accounting API 集成测试。"""

    async def test_list_ar_vouchers_returns_200(self, fin_app_factory) -> None:
        svc = mock_service(list_ar_vouchers=[_ar_voucher_dict("AR-001"), _ar_voucher_dict("AR-002")])
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/accounting/ar-vouchers")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 2
        assert body[0]["voucher_no"] == "AR-001"
        assert body[0]["receivable_amount"] == "1000.00"

    async def test_list_ap_vouchers_returns_200(self, fin_app_factory) -> None:
        svc = mock_service(list_ap_vouchers=[_ap_voucher_dict("AP-001")])
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/accounting/ap-vouchers", params={"is_overdue": "true"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["payable_amount"] == "2000.00"

    async def test_aging_analysis_returns_200(self, fin_app_factory) -> None:
        result = {
            "as_of_date": "2026-09-03",
            "ar_aging": {"B_0_30": "500.00", "B_31_60": "200.00"},
            "ar_total_unreceived": "700.00",
            "ap_aging": {"B_0_30": "1000.00"},
            "ap_total_unpaid": "1000.00",
        }
        svc = mock_service(get_aging_analysis=result)
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/accounting/aging-analysis")
        assert r.status_code == 200
        body = r.json()
        assert body["as_of_date"] == "2026-09-03"
        assert body["ar_total_unreceived"] == "700.00"

    async def test_create_gl_account_returns_201(self, fin_app_factory) -> None:
        account = make_gl_account("1001")
        svc = mock_service(create_gl_account=account)
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/accounting/gl-accounts",
                json={
                    "account_code": "1001",
                    "account_name": "库存现金",
                    "category": "ASSET",
                    "balance_direction": "DEBIT",
                },
            )
        assert r.status_code == 201
        body = r.json()
        assert body["account_code"] == "1001"
        assert body["category"] == "ASSET"
        assert Decimal(body["closing_balance"]) == Decimal("0")

    async def test_create_gl_voucher_returns_201(self, fin_app_factory) -> None:
        voucher = _balanced_gl_voucher("GL-001")
        svc = mock_service(create_gl_voucher=voucher)
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/accounting/gl-vouchers", json=_gl_voucher_body("GL-001"))
        assert r.status_code == 201
        body = r.json()
        assert body["voucher_no"] == "GL-001"
        assert body["period"] == "2026-09"
        assert body["is_period_closed"] is False

    async def test_create_gl_voucher_unbalanced_rejected_422(self, fin_app_factory) -> None:
        svc = mock_service(
            create_gl_voucher=FINError(FINErrorCode.GL_UNBALANCED, "debit != credit")
        )
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/accounting/gl-vouchers", json=_gl_voucher_body("GL-X"))
        assert r.status_code == 422
        assert r.json()["error_code"] == FINErrorCode.GL_UNBALANCED.value

    async def test_period_close_returns_200(self, fin_app_factory) -> None:
        svc = mock_service(period_close=5)
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/accounting/period-close",
                json={"period": "2026-09", "user_id": "U-001"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["period"] == "2026-09"
        assert body["closed_voucher_count"] == 5

    async def test_period_close_already_closed_rejected_423(self, fin_app_factory) -> None:
        svc = mock_service(
            period_close=FINError(FINErrorCode.GL_PERIOD_CLOSED, "period closed")
        )
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/accounting/period-close",
                json={"period": "2026-09", "user_id": "U-001"},
            )
        assert r.status_code == 423
        assert r.json()["error_code"] == FINErrorCode.GL_PERIOD_CLOSED.value

    async def test_financial_report_returns_200(self, fin_app_factory) -> None:
        data = {"revenue": "100000.00", "cost": "60000.00", "profit": "40000.00"}
        svc = mock_service(get_financial_report=data)
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/accounting/reports/balance-sheet", params={"period": "2026-09"})
        assert r.status_code == 200
        body = r.json()
        assert body["report_type"] == "balance-sheet"
        assert body["data"]["profit"] == "40000.00"

    async def test_create_gl_account_invalid_category_422(self, fin_app_factory) -> None:
        svc = mock_service()
        app = fin_app_factory({get_accounting_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/accounting/gl-accounts",
                json={
                    "account_code": "1001",
                    "account_name": "x",
                    "category": "INVALID",
                    "balance_direction": "DEBIT",
                },
            )
        assert r.status_code == 422