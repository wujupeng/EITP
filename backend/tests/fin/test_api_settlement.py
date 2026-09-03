"""Settlement API 集成测试 - 结算单创建/确认/取消/查询全链路。

覆盖：
- POST /api/v1/fin/settlements 创建结算单（201 + Decimal 字符串）
- POST /api/v1/fin/settlements/{no}/confirm 确认结算单
- POST /api/v1/fin/settlements/{no}/cancel 取消结算单
- GET  /api/v1/fin/settlements/{no} 查询详情（404 不存在）
- GET  /api/v1/fin/settlements 列表 + 过滤
- Decimal 金额在请求/响应中以字符串传递
- 错误码 → HTTP 状态码映射（SETTLEMENT_NOT_FOUND→404, INVALID_TRANSITION→422）
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.interfaces.api.v1.fin.routes._deps import get_settlement_service
from tests.fin.conftest import (
    TENANT_ID,
    make_client,
    make_settlement,
    mock_service,
)


def _create_body(settlement_no: str = "ST-001") -> dict:
    return {
        "settlement_no": settlement_no,
        "settlement_type": "PURCHASE",
        "counterparty_id": "CP-001",
        "counterparty_type": "SUPPLIER",
        "currency": "CNY",
        "lines": [
            {
                "product_id": "P-001",
                "quantity": "10.00",
                "tax_exclusive_unit_price": "100.00",
                "tax_inclusive_unit_price": "113.00",
                "tax_rate": "0.1300",
            }
        ],
    }


class SettlementApiTest:
    """Settlement API 集成测试。"""

    async def test_create_settlement_returns_201_and_decimal_string(self, fin_app_factory) -> None:
        settlement = make_settlement("ST-001")
        svc = mock_service(create_settlement=settlement)
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/settlements", json=_create_body())
        assert r.status_code == 201
        body = r.json()
        assert body["settlement_no"] == "ST-001"
        assert body["status"] == "DRAFT"
        # Decimal 金额以字符串传递，精确到分
        assert body["settlement_amount"] == "1130.00"
        assert body["tax_amount"] == "130.00"
        assert body["lines"][0]["line_amount"] == "1130.00"

    async def test_create_settlement_empty_lines_rejected_422(self, fin_app_factory) -> None:
        svc = mock_service()
        app = fin_app_factory({get_settlement_service: lambda: svc})
        body = _create_body()
        body["lines"] = []
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/settlements", json=body)
        assert r.status_code == 422

    async def test_create_settlement_invalid_type_rejected_422(self, fin_app_factory) -> None:
        svc = mock_service()
        app = fin_app_factory({get_settlement_service: lambda: svc})
        body = _create_body()
        body["settlement_type"] = "INVALID"
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/settlements", json=body)
        assert r.status_code == 422

    async def test_confirm_settlement_returns_200(self, fin_app_factory) -> None:
        confirmed = make_settlement("ST-001").confirm()
        svc = mock_service(confirm_settlement=confirmed)
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/settlements/ST-001/confirm")
        assert r.status_code == 200
        assert r.json()["status"] == "CONFIRMED"

    async def test_confirm_settlement_not_found_returns_404(self, fin_app_factory) -> None:
        svc = mock_service(
            confirm_settlement=FINError(FINErrorCode.SETTLEMENT_NOT_FOUND, "not found")
        )
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/settlements/ST-X/confirm")
        assert r.status_code == 404
        assert r.json()["error_code"] == FINErrorCode.SETTLEMENT_NOT_FOUND.value

    async def test_cancel_settlement_returns_200(self, fin_app_factory) -> None:
        cancelled = make_settlement("ST-001").cancel()
        svc = mock_service(cancel_settlement=cancelled)
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/settlements/ST-001/cancel", json={"reason": "测试取消"})
        assert r.status_code == 200
        assert r.json()["status"] == "CANCELLED"

    async def test_cancel_settled_rejected_422(self, fin_app_factory) -> None:
        svc = mock_service(
            cancel_settlement=FINError(FINErrorCode.SETTLEMENT_INVALID_TRANSITION, "bad transition")
        )
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/settlements/ST-001/cancel", json={"reason": ""})
        assert r.status_code == 422
        assert r.json()["error_code"] == FINErrorCode.SETTLEMENT_INVALID_TRANSITION.value

    async def test_get_settlement_detail_returns_200(self, fin_app_factory) -> None:
        settlement = make_settlement("ST-001")
        repo = mock_service(get_by_no=settlement)
        svc = mock_service()
        svc._settlement_repo = repo
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/settlements/ST-001")
        assert r.status_code == 200
        body = r.json()
        assert body["settlement_no"] == "ST-001"
        assert body["settlement_amount"] == "1130.00"

    async def test_get_settlement_not_found_returns_404(self, fin_app_factory) -> None:
        repo = mock_service(get_by_no=None)
        svc = mock_service()
        svc._settlement_repo = repo
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/settlements/ST-X")
        assert r.status_code == 404
        assert r.json()["error_code"] == FINErrorCode.SETTLEMENT_NOT_FOUND.value

    async def test_list_settlements_returns_200(self, fin_app_factory) -> None:
        items = [make_settlement("ST-001"), make_settlement("ST-002")]
        repo = mock_service(list_settlements=items)
        svc = mock_service()
        svc._settlement_repo = repo
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/settlements", params={"status": "DRAFT", "limit": 50})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert body["items"][0]["settlement_no"] == "ST-001"
        assert body["limit"] == 50

    async def test_list_settlements_empty_returns_200(self, fin_app_factory) -> None:
        repo = mock_service(list_settlements=[])
        svc = mock_service()
        svc._settlement_repo = repo
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.get("/api/v1/fin/settlements")
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["items"] == []

    async def test_decimal_amount_precision_in_response(self, fin_app_factory) -> None:
        """验证响应金额始终保持 2 位小数字符串格式。"""
        settlement = make_settlement("ST-PREC")
        svc = mock_service(create_settlement=settlement)
        app = fin_app_factory({get_settlement_service: lambda: svc})
        async with make_client(app) as c:
            r = await c.post("/api/v1/fin/settlements", json=_create_body("ST-PREC"))
        body = r.json()
        for field in ("settlement_amount", "tax_amount"):
            val = body[field]
            assert isinstance(val, str)
            assert "." in val
            assert len(val.split(".")[1]) == 2