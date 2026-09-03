"""Invoice API 集成测试 - 发票开具/匹配/校验/归档/作废/查询全链路。

覆盖：
- POST /api/v1/fin/invoices 开具发票（201）
- POST /api/v1/fin/invoices/{no}/match 匹配发票
- POST /api/v1/fin/invoices/{no}/verify 校验发票
- POST /api/v1/fin/invoices/{no}/archive 归档发票
- POST /api/v1/fin/invoices/{no}/void 作废发票
- GET  /api/v1/fin/invoices 列表
- 已归档发票不可变拒绝（INVOICE_ARCHIVED_IMMUTABLE → 403）
- 已归档发票作废拒绝（INVOICE_ARCHIVED_VOID_FORBIDDEN → 403）
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.interfaces.api.v1.fin.routes._deps import get_invoice_service
from tests.fin.conftest import make_client, make_invoice, mock_service


def _issue_body(invoice_no: str = "INV-001") -> dict:
    return {
        "invoice_code": "CODE-001",
        "invoice_no": invoice_no,
        "invoice_type": "GENERAL",
        "buyer_info": {"name": "买方"},
        "seller_info": {"name": "卖方"},
        "currency": "CNY",
        "lines": [
            {
                "product_id": "P-001",
                "product_name": "商品A",
                "quantity": "1.00",
                "tax_exclusive_amount": "100.00",
                "tax_amount": "13.00",
                "tax_inclusive_amount": "113.00",
            }
        ],
    }


class InvoiceApiTest:
    """Invoice API 集成测试。"""

    async def test_issue_invoice_returns_201(self, fin_app_factory) -> None:
        invoice = make_invoice("INV-001").issue()
        svc = mock_service(issue_invoice=invoice)
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/invoices", json=_issue_body())
        assert r.status_code == 201
        body = r.json()
        assert body["invoice_no"] == "INV-001"
        assert body["status"] == "ISSUED"
        assert body["tax_inclusive_amount"] == "113.00"
        assert body["tax_exclusive_amount"] == "100.00"
        assert body["tax_amount"] == "13.00"

    async def test_issue_invoice_invalid_type_rejected_422(self, fin_app_factory) -> None:
        svc = mock_service()
        app = fin_app_factory({get_invoice_service: lambda: svc})
        body = _issue_body()
        body["invoice_type"] = "INVALID"
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/invoices", json=body)
        assert r.status_code == 422

    async def test_match_invoice_returns_200(self, fin_app_factory) -> None:
        result = SimpleNamespace(business_ref_type="SETTLEMENT", business_ref_id="ST-001", score=0.95)
        svc = mock_service(match_invoice=result)
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/invoices/INV-001/match",
                json={
                    "candidates": [
                        {
                            "business_ref_type": "SETTLEMENT",
                            "business_ref_id": "ST-001",
                            "amount": "113.00",
                            "score": 0.9,
                        }
                    ]
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert body["business_ref_type"] == "SETTLEMENT"
        assert body["business_ref_id"] == "ST-001"
        assert body["score"] == 0.95

    async def test_verify_invoice_returns_200(self, fin_app_factory) -> None:
        verified = make_invoice("INV-001").issue().match("SETTLEMENT", "ST-001").verify()
        svc = mock_service(verify_invoice=verified)
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/invoices/INV-001/verify", json={})
        assert r.status_code == 200
        assert r.json()["status"] == "VERIFIED"

    async def test_archive_invoice_returns_200(self, fin_app_factory) -> None:
        archived = make_invoice("INV-001").issue().match("S", "1").verify().archive()
        svc = mock_service(archive_invoice=archived)
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/invoices/INV-001/archive", json={})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ARCHIVED"
        assert body["archive_hash"] is not None
        assert len(body["archive_hash"]) == 64  # SHA-256 hex

    async def test_archive_invoice_immutable_rejected_403(self, fin_app_factory) -> None:
        svc = mock_service(
            archive_invoice=FINError(FINErrorCode.INVOICE_ARCHIVED_IMMUTABLE, "archived immutable")
        )
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/invoices/INV-001/archive", json={})
        assert r.status_code == 403
        assert r.json()["error_code"] == FINErrorCode.INVOICE_ARCHIVED_IMMUTABLE.value

    async def test_void_invoice_returns_200(self, fin_app_factory) -> None:
        voided = make_invoice("INV-001").issue().void_invoice("作废原因")
        svc = mock_service(void_invoice=voided)
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/invoices/INV-001/void", json={"reason": "作废原因"}
            )
        assert r.status_code == 200
        assert r.json()["status"] == "VOID"

    async def test_void_archived_invoice_rejected_403(self, fin_app_factory) -> None:
        svc = mock_service(
            void_invoice=FINError(FINErrorCode.INVOICE_ARCHIVED_VOID_FORBIDDEN, "archived cannot void")
        )
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post(
                "/api/v1/fin/invoices/INV-001/void", json={"reason": "尝试作废已归档"}
            )
        assert r.status_code == 403
        assert r.json()["error_code"] == FINErrorCode.INVOICE_ARCHIVED_VOID_FORBIDDEN.value

    async def test_void_invoice_without_reason_rejected_422(self, fin_app_factory) -> None:
        svc = mock_service(
            void_invoice=FINError(FINErrorCode.INVOICE_VOID_REASON_REQUIRED, "reason required")
        )
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/invoices/INV-001/void", json={"reason": ""})
        assert r.status_code == 422
        assert r.json()["error_code"] == FINErrorCode.INVOICE_VOID_REASON_REQUIRED.value

    async def test_list_invoices_returns_200(self, fin_app_factory) -> None:
        items = [make_invoice("INV-001").issue(), make_invoice("INV-002").issue()]
        repo = mock_service(list_invoices=items)
        svc = mock_service()
        svc._invoice_repo = repo
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/invoices", params={"status": "ISSUED"})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert body["items"][0]["invoice_no"] == "INV-001"

    async def test_get_invoice_not_found_404(self, fin_app_factory) -> None:
        repo = mock_service(get_by_no=None)
        svc = mock_service()
        svc._invoice_repo = repo
        app = fin_app_factory({get_invoice_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/invoices/INV-X")
        assert r.status_code == 404
        assert r.json()["error_code"] == FINErrorCode.INVOICE_NOT_FOUND.value