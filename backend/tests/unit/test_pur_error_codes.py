"""PUR 错误码与 HTTP 状态码映射单元测试 - PURErrorCode(48) → _status_for_pur_code。

覆盖 404/403/409/422/500 全部分类、_status_for_code 对 PURErrorCode 的分发、
PURError 异常构造（code/message/details）与 DomainError 继承关系。
"""

from __future__ import annotations

import pytest

from app.interfaces.middleware.error_handler import (
    DomainError,
    PURError,
    PURErrorCode,
    _status_for_code,
    _status_for_pur_code,
)


# 期望的分类表（48 个错误码 → HTTP 状态码）
_EXPECTED_STATUS: dict[PURErrorCode, int] = {
    # 404 Not Found
    PURErrorCode.SUPPLIER_NOT_FOUND: 404,
    PURErrorCode.REQUEST_NOT_FOUND: 404,
    PURErrorCode.ORDER_NOT_FOUND: 404,
    PURErrorCode.ORDER_LINE_NOT_FOUND: 404,
    PURErrorCode.RECEIPT_NOT_FOUND: 404,
    PURErrorCode.RETURN_NOT_FOUND: 404,
    PURErrorCode.SETTLEMENT_NOT_FOUND: 404,
    PURErrorCode.INVOICE_NOT_FOUND: 404,
    PURErrorCode.PAYMENT_NOT_FOUND: 404,
    PURErrorCode.ASN_NOT_FOUND: 404,
    PURErrorCode.QUOTATION_NOT_FOUND: 404,
    PURErrorCode.EVALUATION_NOT_FOUND: 404,
    PURErrorCode.SKU_NOT_FOUND: 404,
    PURErrorCode.BUDGET_NOT_FOUND: 404,
    # 403 Forbidden
    PURErrorCode.SUPPLIER_DISABLED: 403,
    PURErrorCode.SUPPLIER_NOT_ACTIVE: 403,
    PURErrorCode.CROSS_TENANT_SUPPLIER_DENIED: 403,
    PURErrorCode.CROSS_TENANT_REF_DENIED: 403,
    PURErrorCode.DIRECT_INVENTORY_MODIFY_DENIED: 403,
    PURErrorCode.DIRECT_COST_MODIFY_DENIED: 403,
    PURErrorCode.REQUEST_NOT_APPROVED: 403,
    PURErrorCode.ORDER_NOT_APPROVED: 403,
    PURErrorCode.RETURN_NOT_APPROVED: 403,
    PURErrorCode.OWNERSHIP_REQUIRED: 403,
    PURErrorCode.PORTAL_PERMISSION_DENIED: 403,
    # 409 Conflict
    PURErrorCode.SUPPLIER_CODE_DUPLICATE: 409,
    PURErrorCode.IDEMPOTENCY_KEY_CONFLICT: 409,
    PURErrorCode.IDEMPOTENCY_KEY_REQUIRED: 409,
    PURErrorCode.PAYMENT_ALREADY_COMPLETED: 409,
    # 422 Unprocessable
    PURErrorCode.SUPPLIER_SCOPE_MISMATCH: 422,
    PURErrorCode.REQUEST_BUDGET_EXCEEDED: 422,
    PURErrorCode.SKU_DISABLED: 422,
    PURErrorCode.ORDER_INVALID_STATE_TRANSITION: 422,
    PURErrorCode.ORDER_CANCEL_WITH_RECEIVED: 422,
    PURErrorCode.RECEIPT_OVER_RECEIVED: 422,
    PURErrorCode.RECEIPT_ORDER_INVALID: 422,
    PURErrorCode.RETURN_OVER_RETURNED: 422,
    PURErrorCode.SETTLEMENT_RECONCILE_DIFF_EXCEEDED: 422,
    PURErrorCode.INVOICE_MATCH_DIFF_EXCEEDED: 422,
    PURErrorCode.WMS_INV_INCONSISTENT: 422,
    PURErrorCode.RMQ_INVALID_STATE_TRANSITION: 422,
    PURErrorCode.FRAMEWORK_AGREEMENT_EXPIRED: 422,
    PURErrorCode.FRAMEWORK_AGREEMENT_QTY_EXCEEDED: 422,
    PURErrorCode.APPROVAL_TIMEOUT: 422,
    # 500 Internal
    PURErrorCode.WMS_RECEIVING_FAILED: 500,
    PURErrorCode.RETURN_INVENTORY_FAILED: 500,
    PURErrorCode.FINANCIAL_API_FAILED: 500,
    PURErrorCode.SERVICE_UNAVAILABLE: 500,
}


class PURErrorCodeTest:
    """PURErrorCode 枚举与 HTTP 状态码映射测试。"""

    def test_all_48_codes_classified(self) -> None:
        # 期望表覆盖全部 PURErrorCode 成员，无遗漏、无多余
        all_codes = set(PURErrorCode)
        classified = set(_EXPECTED_STATUS)
        assert classified == all_codes
        assert len(all_codes) == 48

    def test_every_code_maps_to_expected_status(self) -> None:
        for code, expected in _EXPECTED_STATUS.items():
            assert _status_for_pur_code(code) == expected, f"{code} 映射不符"

    def test_status_for_code_dispatches_pur_error_code(self) -> None:
        # _status_for_code 应识别 PURErrorCode 并走 PUR 分支
        assert _status_for_code(PURErrorCode.SUPPLIER_NOT_FOUND) == 404
        assert _status_for_code(PURErrorCode.SUPPLIER_NOT_ACTIVE) == 403
        assert _status_for_code(PURErrorCode.SUPPLIER_CODE_DUPLICATE) == 409
        assert _status_for_code(PURErrorCode.ORDER_INVALID_STATE_TRANSITION) == 422
        assert _status_for_code(PURErrorCode.WMS_RECEIVING_FAILED) == 500

    def test_status_distribution_counts(self) -> None:
        from collections import Counter

        counts = Counter(_status_for_pur_code(c) for c in PURErrorCode)
        assert counts[404] == 14
        assert counts[403] == 11
        assert counts[409] == 4
        assert counts[422] == 15
        assert counts[500] == 4
        # 无任何 code 落入默认 400
        assert counts.get(400, 0) == 0

    def test_all_codes_carry_eitp_pur_prefix(self) -> None:
        for code in PURErrorCode:
            assert code.value.startswith("EITP_PUR_"), f"{code} 前缀不符"

    def test_codes_are_unique(self) -> None:
        values = [c.value for c in PURErrorCode]
        assert len(values) == len(set(values))


class PURErrorTest:
    """PURError 异常构造与继承测试。"""

    def test_construct_with_code_and_message(self) -> None:
        err = PURError(PURErrorCode.ORDER_NOT_FOUND, "订单不存在")
        assert err.code == PURErrorCode.ORDER_NOT_FOUND
        assert err.message == "订单不存在"
        assert err.details == {}

    def test_construct_with_details(self) -> None:
        err = PURError(
            PURErrorCode.WMS_INV_INCONSISTENT,
            "三边不一致",
            details={"pur": 100, "wms": 90},
        )
        assert err.details == {"pur": 100, "wms": 90}

    def test_is_domain_error_subclass(self) -> None:
        err = PURError(PURErrorCode.SUPPLIER_NOT_ACTIVE, "非active")
        assert isinstance(err, DomainError)
        assert isinstance(err, Exception)

    def test_raise_and_catch_code(self) -> None:
        with pytest.raises(PURError) as exc:
            raise PURError(PURErrorCode.ORDER_CANCEL_WITH_RECEIVED, "已收货不可取消")
        assert exc.value.code == PURErrorCode.ORDER_CANCEL_WITH_RECEIVED
        assert "已收货不可取消" in str(exc.value)

    def test_details_default_is_empty_dict_when_none(self) -> None:
        err = PURError(PURErrorCode.SUPPLIER_NOT_FOUND, "x", details=None)
        assert err.details == {}