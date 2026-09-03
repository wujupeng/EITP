"""Payment API 集成测试 - 付款申请/审批/执行/银行回调/查询全链路。

覆盖：
- POST /api/v1/fin/payments 申请付款（201）
- POST /api/v1/fin/payments/{no}/approve 审批付款
- POST /api/v1/fin/payments/{no}/execute 执行付款
- POST /api/v1/fin/payments/{no}/bank-callback 银行回调
- GET  /api/v1/fin/payments/{no} 查询详情（404）
- GET  /api/v1/fin/payments 列表
- 付款超 AP 拒绝（PAYMENT_EXCEED_AP → 422）
- Decimal 金额字符串传递
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import PaymentMethod
from app.interfaces.api.v1.fin.routes._deps import get_payment_service
from tests.fin.conftest import make_client, make_payment, mock_service


def _create_body(payment_no: str = "PAY-001") -> dict:
    return {
        "payment_no": payment_no,
        "ap_voucher_no": "AP-001",
        "payment_amount": "1000.00",
        "payment_method": "BANK_TRANSFER",
        "payment_account": "BANK-001",
        "payee_account": "BANK-002",
        "currency": "CNY",
    }


class PaymentApiTest:
    """Payment API 集成测试。"""

    async def test_request_payment_returns_201(self, fin_app_factory) -> None:
        payment = make_payment("PAY-001")
        svc = mock_service(request_payment=payment)
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/payments", json=_create_body())
        assert r.status_code == 201
        body = r.json()
        assert body["payment_no"] == "PAY-001"
        assert body["status"] == "DRAFT"
        assert body["payment_amount"] == "1000.00"
        assert body["payment_method"] == "BANK_TRANSFER"

    async def test_request_payment_exceed_ap_rejected_422(self, fin_app_factory) -> None:
        svc = mock_service(
            request_payment=FINError(FINErrorCode.PAYMENT_EXCEED_AP, "exceed ap unpaid")
        )
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/payments", json=_create_body())
        assert r.status_code == 422
        assert r.json()["error_code"] == FINErrorCode.PAYMENT_EXCEED_AP.value

    async def test_request_payment_invalid_method_rejected_422(self, fin_app_factory) -> None:
        svc = mock_service()
        app = fin_app_factory({get_payment_service: lambda: svc})
        body = _create_body()
        body["payment_method"] = "INVALID"
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/payments", json=body)
        assert r.status_code == 422

    async def test_approve_payment_returns_200(self, fin_app_factory) -> None:
        approved = make_payment("PAY-001").submit().approve("U-001", "同意")
        svc = mock_service(approve_payment=approved)
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/payments/PAY-001/approve",
                json={"approver_id": "U-001", "approved": True, "approval_opinion": "同意"},
            )
        assert r.status_code == 200
        assert r.json()["status"] == "APPROVED"
        assert r.json()["approver_id"] == "U-001"

    async def test_reject_payment_returns_200(self, fin_app_factory) -> None:
        rejected = make_payment("PAY-001").submit().reject("U-001", "拒绝")
        svc = mock_service(reject_payment=rejected)
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/payments/PAY-001/approve",
                json={"approver_id": "U-001", "approved": False, "approval_opinion": "拒绝"},
            )
        assert r.status_code == 200
        assert r.json()["status"] == "DRAFT"

    async def test_execute_payment_returns_200(self, fin_app_factory) -> None:
        executing = make_payment("PAY-001").submit().approve("U-001").execute()
        svc = mock_service(execute_payment=executing)
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/payments/PAY-001/execute")
        assert r.status_code == 200
        assert r.json()["status"] == "EXECUTING"

    async def test_execute_payment_invalid_transition_422(self, fin_app_factory) -> None:
        svc = mock_service(
            execute_payment=FINError(FINErrorCode.PAYMENT_INVALID_TRANSITION, "bad")
        )
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/payments/PAY-001/execute")
        assert r.status_code == 422
        assert r.json()["error_code"] == FINErrorCode.PAYMENT_INVALID_TRANSITION.value

    async def test_bank_callback_returns_200(self, fin_app_factory) -> None:
        success = (
            make_payment("PAY-001")
            .submit()
            .approve("U-001")
            .execute()
            .bank_callback_success("BANK-REF-001")
        )
        svc = mock_service(bank_callback=success)
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/payments/PAY-001/bank-callback",
                json={"callback_payload": {"status": "SUCCESS", "bank_ref": "BANK-REF-001"}},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "SUCCESS"
        assert body["bank_ref"] == "BANK-REF-001"

    async def test_get_payment_detail_returns_200(self, fin_app_factory) -> None:
        payment = make_payment("PAY-001")
        repo = mock_service(get_by_no=payment)
        svc = mock_service()
        svc._payment_repo = repo
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/payments/PAY-001")
        assert r.status_code == 200
        assert r.json()["payment_no"] == "PAY-001"

    async def test_get_payment_not_found_404(self, fin_app_factory) -> None:
        repo = mock_service(get_by_no=None)
        svc = mock_service()
        svc._payment_repo = repo
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/payments/PAY-X")
        assert r.status_code == 404
        assert r.json()["error_code"] == FINErrorCode.PAYMENT_NOT_FOUND.value

    async def test_list_payments_returns_200(self, fin_app_factory) -> None:
        items = [make_payment("PAY-001"), make_payment("PAY-002")]
        repo = mock_service(list_payments=items)
        svc = mock_service()
        svc._payment_repo = repo
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/payments", params={"status": "DRAFT"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert body["items"][0]["payment_no"] == "PAY-001"

    async def test_payment_decimal_amount_string_in_response(self, fin_app_factory) -> None:
        payment = make_payment("PAY-DEC")
        svc = mock_service(request_payment=payment)
        app = fin_app_factory({get_payment_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/payments", json=_create_body("PAY-DEC"))
        val = r.json()["payment_amount"]
        assert isinstance(val, str)
        assert val == "1000.00"