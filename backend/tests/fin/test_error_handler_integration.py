"""红线测试 T15-11 - 错误处理集成：FINError → HTTP 状态码完整映射。

验证 EITP-FIN-001 的错误处理链：
- 每个 FINErrorCode 映射到正确的 HTTP 状态码
- 通过 FastAPI app 验证完整链路：FINError → handler → JSONResponse
- 覆盖所有状态码类别：403/404/409/422/423/500/502/400(默认)
- 响应体格式：{error_code, message, details}
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.interfaces.middleware.error_handler import (
    FINErrorCode as MiddlewareFINErrorCode,
    _status_for_fin_code,
)


# --------------------------------------------------------------------------- #
# 辅助：构建带 FINError handler 和触发端点的测试 app
# --------------------------------------------------------------------------- #

def make_error_app() -> FastAPI:
    """创建带 FINError handler 和触发端点的测试 app。

    /trigger/{code_name}  端点直接 raise FINError(code)，验证完整错误处理链。
    """
    app = FastAPI()

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

    @app.get("/trigger/{code_name}")
    async def trigger_error(code_name: str) -> Any:
        code = FINErrorCode[code_name]
        raise FINError(code, f"triggered {code_name}")

    @app.get("/trigger-details/{code_name}")
    async def trigger_error_with_details(code_name: str) -> Any:
        code = FINErrorCode[code_name]
        raise FINError(
            code,
            f"triggered {code_name}",
            details={"entity": "test", "field": "value"},
        )

    return app


# --------------------------------------------------------------------------- #
# 按状态码分类的 FINErrorCode
# --------------------------------------------------------------------------- #

_403_CODES = [
    FINErrorCode.PAYMENT_APPROVAL_EXCEED_AUTHORITY,
    FINErrorCode.TREASURY_TRANSFER_UNAUTHORIZED,
    FINErrorCode.GL_DELETE_FORBIDDEN,
    FINErrorCode.INVOICE_ARCHIVED_IMMUTABLE,
    FINErrorCode.INVOICE_ARCHIVED_VOID_FORBIDDEN,
    FINErrorCode.PAYMENT_CANCEL_FORBIDDEN,
    FINErrorCode.COLLECTION_RECORD_IMMUTABLE,
]

_404_CODES = [
    FINErrorCode.SETTLEMENT_NOT_FOUND,
    FINErrorCode.PAYMENT_NOT_FOUND,
    FINErrorCode.VOUCHER_NOT_FOUND,
    FINErrorCode.RECEIPT_NOT_FOUND,
    FINErrorCode.INVOICE_NOT_FOUND,
    FINErrorCode.RECON_NOT_FOUND,
    FINErrorCode.RECON_DIFF_NOT_FOUND,
    FINErrorCode.GL_ACCOUNT_NOT_FOUND,
    FINErrorCode.GL_VOUCHER_NOT_FOUND,
    FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND,
    FINErrorCode.TREASURY_TRANSFER_NOT_FOUND,
    FINErrorCode.COLLECTION_TASK_NOT_FOUND,
    FINErrorCode.VOUCHER_RED_ORIGINAL_NOT_FOUND,
    FINErrorCode.GL_RED_VOUCHER_ORIGINAL_NOT_FOUND,
]

_409_CODES = [
    FINErrorCode.SETTLEMENT_DUPLICATE,
    FINErrorCode.PAYMENT_DUPLICATE,
    FINErrorCode.PAYMENT_BANK_REF_DUPLICATE,
    FINErrorCode.RECEIPT_DUPLICATE_BANK_REF,
    FINErrorCode.INVOICE_DUPLICATE,
    FINErrorCode.RECON_DUPLICATE,
    FINErrorCode.GL_ACCOUNT_DUPLICATE,
    FINErrorCode.TREASURY_ACCOUNT_DUPLICATE,
    FINErrorCode.SETTLEMENT_ALREADY_SETTLED,
    FINErrorCode.PAYMENT_ALREADY_SUCCESS,
    FINErrorCode.RECEIPT_ALREADY_WRITEOFF,
    FINErrorCode.RECON_DIFF_ALREADY_HANDLED,
    FINErrorCode.VOUCHER_ALREADY_SETTLED,
    FINErrorCode.COLLECTION_TASK_ALREADY_RESOLVED,
]

_422_CODES = [
    FINErrorCode.SETTLEMENT_PUR_NOT_RECEIVED,
    FINErrorCode.SETTLEMENT_SAL_NOT_SHIPPED,
    FINErrorCode.SETTLEMENT_QTY_EXCEED_RECEIVED,
    FINErrorCode.SETTLEMENT_INVALID_TRANSITION,
    FINErrorCode.SETTLEMENT_LINE_EMPTY,
    FINErrorCode.MONEY_FLOAT_FORBIDDEN,
    FINErrorCode.MONEY_PRECISION_LOSS,
    FINErrorCode.MONEY_NEGATIVE_FORBIDDEN,
    FINErrorCode.MONEY_CURRENCY_MISMATCH,
    FINErrorCode.PAYMENT_EXCEED_AP,
    FINErrorCode.PAYMENT_INVALID_TRANSITION,
    FINErrorCode.PAYMENT_OVERPAY,
    FINErrorCode.AP_UNBALANCED,
    FINErrorCode.AR_UNBALANCED,
    FINErrorCode.AR_AP_UNBALANCED,
    FINErrorCode.RECEIPT_WRITEOFF_EXCEED,
    FINErrorCode.RECEIPT_INVALID_TRANSITION,
    FINErrorCode.RECEIPT_AMOUNT_MISMATCH,
    FINErrorCode.INVOICE_AMOUNT_MISMATCH,
    FINErrorCode.INVOICE_RED_INVALID,
    FINErrorCode.INVOICE_VERIFY_FAIL,
    FINErrorCode.INVOICE_LINE_AMOUNT_MISMATCH,
    FINErrorCode.INVOICE_VOID_REASON_REQUIRED,
    FINErrorCode.RECON_WRITEOFF_NO_EVIDENCE,
    FINErrorCode.RECON_INVALID_TRANSITION,
    FINErrorCode.RECON_PERIOD_OVERLAP,
    FINErrorCode.GL_UNBALANCED,
    FINErrorCode.GL_PERIOD_UNBALANCED,
    FINErrorCode.TREASURY_INSUFFICIENT_BALANCE,
    FINErrorCode.TREASURY_TRANSFER_SAME_ACCOUNT,
    FINErrorCode.TREASURY_TRANSFER_INVALID_TRANSITION,
    FINErrorCode.TREASURY_FREEZE_EXCEED,
    FINErrorCode.SETTLEMENT_CROSS_TENANT_NOT_CONFIRMED,
    FINErrorCode.SETTLEMENT_CANCEL_WITH_PAYMENT,
    FINErrorCode.VOUCHER_RED_AMOUNT_EXCEED,
]

_423_CODES = [
    FINErrorCode.CORE_FREEZE_VIOLATION,
    FINErrorCode.GL_PERIOD_CLOSED,
]

_500_CODES = [
    FINErrorCode.INTERNAL_ERROR,
]

_502_CODES = [
    FINErrorCode.PAYMENT_ACCOUNT_ENCRYPT_FAIL,
    FINErrorCode.TREASURY_TRANSFER_FAILED,
    FINErrorCode.RECEIPT_NO_EVIDENCE,
]


class TestStatusMappingUnit:
    """_status_for_fin_code 单元测试 - 每个错误码映射正确。"""

    @pytest.mark.parametrize("code", _403_CODES, ids=[c.name for c in _403_CODES])
    def test_403_mapping(self, code: FINErrorCode) -> None:
        mw_code = MiddlewareFINErrorCode(code.value)
        assert _status_for_fin_code(mw_code) == 403

    @pytest.mark.parametrize("code", _404_CODES, ids=[c.name for c in _404_CODES])
    def test_404_mapping(self, code: FINErrorCode) -> None:
        mw_code = MiddlewareFINErrorCode(code.value)
        assert _status_for_fin_code(mw_code) == 404

    @pytest.mark.parametrize("code", _409_CODES, ids=[c.name for c in _409_CODES])
    def test_409_mapping(self, code: FINErrorCode) -> None:
        mw_code = MiddlewareFINErrorCode(code.value)
        assert _status_for_fin_code(mw_code) == 409

    @pytest.mark.parametrize("code", _422_CODES, ids=[c.name for c in _422_CODES])
    def test_422_mapping(self, code: FINErrorCode) -> None:
        mw_code = MiddlewareFINErrorCode(code.value)
        assert _status_for_fin_code(mw_code) == 422

    @pytest.mark.parametrize("code", _423_CODES, ids=[c.name for c in _423_CODES])
    def test_423_mapping(self, code: FINErrorCode) -> None:
        mw_code = MiddlewareFINErrorCode(code.value)
        assert _status_for_fin_code(mw_code) == 423

    @pytest.mark.parametrize("code", _500_CODES, ids=[c.name for c in _500_CODES])
    def test_500_mapping(self, code: FINErrorCode) -> None:
        mw_code = MiddlewareFINErrorCode(code.value)
        assert _status_for_fin_code(mw_code) == 500

    @pytest.mark.parametrize("code", _502_CODES, ids=[c.name for c in _502_CODES])
    def test_502_mapping(self, code: FINErrorCode) -> None:
        mw_code = MiddlewareFINErrorCode(code.value)
        assert _status_for_fin_code(mw_code) == 502

    def test_all_codes_covered(self) -> None:
        """所有 FINErrorCode 都被分类覆盖。"""
        all_categorized = (
            set(_403_CODES)
            | set(_404_CODES)
            | set(_409_CODES)
            | set(_422_CODES)
            | set(_423_CODES)
            | set(_500_CODES)
            | set(_502_CODES)
        )
        all_codes = set(FINErrorCode)
        uncovered = all_codes - all_categorized
        assert uncovered == set(), f"未覆盖的错误码: {[c.name for c in uncovered]}"

    def test_no_code_in_multiple_categories(self) -> None:
        """每个错误码只在一个分类中。"""
        all_lists = [_403_CODES, _404_CODES, _409_CODES, _422_CODES, _423_CODES, _500_CODES, _502_CODES]
        total = sum(len(lst) for lst in all_lists)
        unique = len(set(code for lst in all_lists for code in lst))
        assert total == unique, f"存在重复分类: total={total}, unique={unique}"


class TestErrorHandlerIntegration:
    """通过 FastAPI app 验证完整错误处理链。"""

    @pytest.mark.parametrize("code", _403_CODES, ids=[c.name for c in _403_CODES])
    async def test_403_through_api(self, code: FINErrorCode) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/trigger/{code.name}")
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_code"] == code.value
        assert body["message"] == f"triggered {code.name}"

    @pytest.mark.parametrize("code", _404_CODES, ids=[c.name for c in _404_CODES])
    async def test_404_through_api(self, code: FINErrorCode) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/trigger/{code.name}")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_code"] == code.value

    @pytest.mark.parametrize("code", _409_CODES, ids=[c.name for c in _409_CODES])
    async def test_409_through_api(self, code: FINErrorCode) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/trigger/{code.name}")
        assert resp.status_code == 409
        body = resp.json()
        assert body["error_code"] == code.value

    @pytest.mark.parametrize("code", _422_CODES, ids=[c.name for c in _422_CODES])
    async def test_422_through_api(self, code: FINErrorCode) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/trigger/{code.name}")
        assert resp.status_code == 422
        body = resp.json()
        assert body["error_code"] == code.value

    @pytest.mark.parametrize("code", _423_CODES, ids=[c.name for c in _423_CODES])
    async def test_423_through_api(self, code: FINErrorCode) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/trigger/{code.name}")
        assert resp.status_code == 423
        body = resp.json()
        assert body["error_code"] == code.value

    @pytest.mark.parametrize("code", _500_CODES, ids=[c.name for c in _500_CODES])
    async def test_500_through_api(self, code: FINErrorCode) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/trigger/{code.name}")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error_code"] == code.value

    @pytest.mark.parametrize("code", _502_CODES, ids=[c.name for c in _502_CODES])
    async def test_502_through_api(self, code: FINErrorCode) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(f"/trigger/{code.name}")
        assert resp.status_code == 502
        body = resp.json()
        assert body["error_code"] == code.value


class TestErrorResponseFormat:
    """错误响应体格式验证。"""

    async def test_response_has_error_code_field(self) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/trigger/SETTLEMENT_NOT_FOUND")
        body = resp.json()
        assert "error_code" in body
        assert "message" in body
        assert "details" in body

    async def test_response_error_code_has_eitp_fin_prefix(self) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/trigger/PAYMENT_NOT_FOUND")
        body = resp.json()
        assert body["error_code"].startswith("EITP_FIN_")

    async def test_response_details_empty_by_default(self) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/trigger/SETTLEMENT_NOT_FOUND")
        body = resp.json()
        assert body["details"] == {}

    async def test_response_details_populated_when_provided(self) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/trigger-details/SETTLEMENT_NOT_FOUND")
        body = resp.json()
        assert body["details"]["entity"] == "test"
        assert body["details"]["field"] == "value"

    async def test_core_freeze_returns_423(self) -> None:
        app = make_error_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/trigger/CORE_FREEZE_VIOLATION")
        assert resp.status_code == 423
        assert resp.json()["error_code"] == "EITP_FIN_CORE_FREEZE_VIOLATION"