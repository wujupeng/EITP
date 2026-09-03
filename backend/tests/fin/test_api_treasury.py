"""Treasury API 集成测试 - 资金账户/调拨/冻结/预测全链路。

覆盖：
- POST /api/v1/fin/treasury/accounts 创建账户（201）
- GET  /api/v1/fin/treasury/accounts 账户列表
- GET  /api/v1/fin/treasury/accounts/{id}/balance 账户余额
- POST /api/v1/fin/treasury/transfers 创建调拨
- POST /api/v1/fin/treasury/transfers/{no}/approve 审批调拨
- POST /api/v1/fin/treasury/accounts/{id}/freeze 冻结账户
- GET  /api/v1/fin/treasury/forecast 现金流预测
- TREASURY_INSUFFICIENT_BALANCE → 422, TREASURY_FREEZE_EXCEED → 422,
  TREASURY_ACCOUNT_NOT_FOUND → 404
"""

from __future__ import annotations

from uuid import uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.money import Money
from app.interfaces.api.v1.fin.routes._deps import get_treasury_service
from tests.fin.conftest import make_client, make_treasury_account, make_treasury_transfer, mock_service


def _account_dict(account_no: str = "BANK-001") -> dict:
    return {
        "account_id": str(uuid4()),
        "account_no": account_no,
        "account_type": "BANK",
        "currency": "CNY",
        "balance": "10000.00",
        "frozen_amount": "0.00",
        "available_balance": "10000.00",
    }


def _transfer_body(transfer_no: str = "TF-001") -> dict:
    return {
        "transfer_no": transfer_no,
        "from_account_id": str(uuid4()),
        "to_account_id": str(uuid4()),
        "transfer_amount": "500.00",
        "reason": "调拨",
        "currency": "CNY",
    }


class TreasuryApiTest:
    """Treasury API 集成测试。"""

    async def test_create_account_returns_201(self, fin_app_factory) -> None:
        account = make_treasury_account("BANK-001")
        svc = mock_service(create_treasury_account=account)
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/treasury/accounts",
                json={"account_no": "BANK-001", "account_type": "BANK", "currency": "CNY", "opening_balance": "10000.00"},
            )
        assert r.status_code == 201
        body = r.json()
        assert body["account_no"] == "BANK-001"
        assert body["balance"] == "10000.00"
        assert body["available_balance"] == "10000.00"

    async def test_list_accounts_returns_200(self, fin_app_factory) -> None:
        svc = mock_service(list_treasury_accounts=[_account_dict("BANK-001"), _account_dict("BANK-002")])
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/treasury/accounts")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 2
        assert body[0]["account_no"] == "BANK-001"

    async def test_get_account_balance_returns_200(self, fin_app_factory) -> None:
        account = make_treasury_account("BANK-001")
        repo = mock_service(get_by_id=account)
        balance = {
            "account_no": "BANK-001",
            "currency": "CNY",
            "balance": "10000.00",
            "frozen_amount": "0.00",
            "available_balance": "10000.00",
        }
        svc = mock_service(get_account_balance=balance)
        svc._account_repo = repo
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get(f"/api/v1/fin/treasury/accounts/{account.account_id}/balance")
        assert r.status_code == 200
        body = r.json()
        assert body["account_no"] == "BANK-001"
        assert body["available_balance"] == "10000.00"

    async def test_get_account_balance_not_found_404(self, fin_app_factory) -> None:
        repo = mock_service(get_by_id=None)
        svc = mock_service()
        svc._account_repo = repo
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get(f"/api/v1/fin/treasury/accounts/{uuid4()}/balance")
        assert r.status_code == 404
        assert r.json()["error_code"] == FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND.value

    async def test_create_transfer_returns_201(self, fin_app_factory) -> None:
        transfer = make_treasury_transfer("TF-001")
        svc = mock_service(request_treasury_transfer=transfer)
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/treasury/transfers", json=_transfer_body("TF-001"))
        assert r.status_code == 201
        body = r.json()
        assert body["transfer_no"] == "TF-001"
        assert body["status"] == "PENDING_APPROVAL"
        assert body["transfer_amount"] == "500.00"

    async def test_create_transfer_insufficient_balance_422(self, fin_app_factory) -> None:
        svc = mock_service(
            request_treasury_transfer=FINError(FINErrorCode.TREASURY_INSUFFICIENT_BALANCE, "insufficient")
        )
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/treasury/transfers", json=_transfer_body("TF-X"))
        assert r.status_code == 422
        assert r.json()["error_code"] == FINErrorCode.TREASURY_INSUFFICIENT_BALANCE.value

    async def test_approve_transfer_returns_200(self, fin_app_factory) -> None:
        transfer = make_treasury_transfer("TF-001").approve("U-001")
        svc = mock_service(approve_treasury_transfer=transfer)
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/treasury/transfers/TF-001/approve",
                json={"approver_id": "U-001"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "APPROVED"
        assert "U-001" in body["approver_ids"]

    async def test_freeze_account_returns_200(self, fin_app_factory) -> None:
        account = make_treasury_account("BANK-001")
        frozen = account.freeze(Money("1000.00"))
        repo = mock_service(get_by_id=account)
        svc = mock_service(freeze_account=frozen)
        svc._account_repo = repo
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                f"/api/v1/fin/treasury/accounts/{account.account_id}/freeze",
                json={"amount": "1000.00", "currency": "CNY"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["frozen_amount"] == "1000.00"
        assert body["available_balance"] == "9000.00"

    async def test_freeze_exceed_rejected_422(self, fin_app_factory) -> None:
        account = make_treasury_account("BANK-001")
        repo = mock_service(get_by_id=account)
        svc = mock_service(
            freeze_account=FINError(FINErrorCode.TREASURY_FREEZE_EXCEED, "freeze exceed")
        )
        svc._account_repo = repo
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                f"/api/v1/fin/treasury/accounts/{account.account_id}/freeze",
                json={"amount": "99999.00", "currency": "CNY"},
            )
        assert r.status_code == 422
        assert r.json()["error_code"] == FINErrorCode.TREASURY_FREEZE_EXCEED.value

    async def test_forecast_returns_200(self, fin_app_factory) -> None:
        result = {
            "forecast_date": "2026-09-03",
            "forecast_days": 30,
            "total_balance": "50000.00",
            "total_frozen": "1000.00",
            "total_available": "49000.00",
            "pending_outflow": "5000.00",
            "projected_available": "44000.00",
            "account_count": 3,
        }
        svc = mock_service(get_cash_flow_forecast=result)
        app = fin_app_factory({get_treasury_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/treasury/forecast", params={"forecast_days": 30})
        assert r.status_code == 200
        body = r.json()
        assert body["total_available"] == "49000.00"
        assert body["projected_available"] == "44000.00"
        assert body["account_count"] == 3