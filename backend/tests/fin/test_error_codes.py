"""FIN 错误码与 HTTP 状态码映射单元测试。

覆盖：
- FINErrorCode 枚举完整性（76 个错误码，全部 EITP_FIN_ 前缀）
- 错误码唯一性
- _status_for_fin_code HTTP 状态码映射（403/404/409/422/423/500/502）
- _status_for_code 对 FINErrorCode 的分发
- FINError 异常构造与属性
"""

from __future__ import annotations

from collections import Counter

import pytest

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.interfaces.middleware.error_handler import (
    DomainError,
    FINErrorCode as MiddlewareFINErrorCode,
    _status_for_code,
    _status_for_fin_code,
)

# 期望的 HTTP 状态码分类表（76 个错误码 → HTTP 状态码）
_EXPECTED_STATUS: dict[FINErrorCode, int] = {
    # 403 Forbidden - 权限/不可变
    FINErrorCode.PAYMENT_APPROVAL_EXCEED_AUTHORITY: 403,
    FINErrorCode.TREASURY_TRANSFER_UNAUTHORIZED: 403,
    FINErrorCode.GL_DELETE_FORBIDDEN: 403,
    FINErrorCode.INVOICE_ARCHIVED_IMMUTABLE: 403,
    FINErrorCode.INVOICE_ARCHIVED_VOID_FORBIDDEN: 403,
    FINErrorCode.PAYMENT_CANCEL_FORBIDDEN: 403,
    FINErrorCode.COLLECTION_RECORD_IMMUTABLE: 403,
    # 404 Not Found
    FINErrorCode.SETTLEMENT_NOT_FOUND: 404,
    FINErrorCode.PAYMENT_NOT_FOUND: 404,
    FINErrorCode.VOUCHER_NOT_FOUND: 404,
    FINErrorCode.RECEIPT_NOT_FOUND: 404,
    FINErrorCode.INVOICE_NOT_FOUND: 404,
    FINErrorCode.RECON_NOT_FOUND: 404,
    FINErrorCode.RECON_DIFF_NOT_FOUND: 404,
    FINErrorCode.GL_ACCOUNT_NOT_FOUND: 404,
    FINErrorCode.GL_VOUCHER_NOT_FOUND: 404,
    FINErrorCode.TREASURY_ACCOUNT_NOT_FOUND: 404,
    FINErrorCode.TREASURY_TRANSFER_NOT_FOUND: 404,
    FINErrorCode.COLLECTION_TASK_NOT_FOUND: 404,
    FINErrorCode.VOUCHER_RED_ORIGINAL_NOT_FOUND: 404,
    FINErrorCode.GL_RED_VOUCHER_ORIGINAL_NOT_FOUND: 404,
    # 409 Conflict - 重复/已完结
    FINErrorCode.SETTLEMENT_DUPLICATE: 409,
    FINErrorCode.PAYMENT_DUPLICATE: 409,
    FINErrorCode.PAYMENT_BANK_REF_DUPLICATE: 409,
    FINErrorCode.RECEIPT_DUPLICATE_BANK_REF: 409,
    FINErrorCode.INVOICE_DUPLICATE: 409,
    FINErrorCode.RECON_DUPLICATE: 409,
    FINErrorCode.GL_ACCOUNT_DUPLICATE: 409,
    FINErrorCode.TREASURY_ACCOUNT_DUPLICATE: 409,
    FINErrorCode.SETTLEMENT_ALREADY_SETTLED: 409,
    FINErrorCode.PAYMENT_ALREADY_SUCCESS: 409,
    FINErrorCode.RECEIPT_ALREADY_WRITEOFF: 409,
    FINErrorCode.RECON_DIFF_ALREADY_HANDLED: 409,
    FINErrorCode.VOUCHER_ALREADY_SETTLED: 409,
    FINErrorCode.COLLECTION_TASK_ALREADY_RESOLVED: 409,
    # 422 Unprocessable - 业务规则/状态机/守恒
    FINErrorCode.SETTLEMENT_PUR_NOT_RECEIVED: 422,
    FINErrorCode.SETTLEMENT_SAL_NOT_SHIPPED: 422,
    FINErrorCode.SETTLEMENT_QTY_EXCEED_RECEIVED: 422,
    FINErrorCode.SETTLEMENT_INVALID_TRANSITION: 422,
    FINErrorCode.SETTLEMENT_LINE_EMPTY: 422,
    FINErrorCode.MONEY_FLOAT_FORBIDDEN: 422,
    FINErrorCode.MONEY_PRECISION_LOSS: 422,
    FINErrorCode.MONEY_NEGATIVE_FORBIDDEN: 422,
    FINErrorCode.MONEY_CURRENCY_MISMATCH: 422,
    FINErrorCode.PAYMENT_EXCEED_AP: 422,
    FINErrorCode.PAYMENT_INVALID_TRANSITION: 422,
    FINErrorCode.PAYMENT_OVERPAY: 422,
    FINErrorCode.AP_UNBALANCED: 422,
    FINErrorCode.AR_UNBALANCED: 422,
    FINErrorCode.AR_AP_UNBALANCED: 422,
    FINErrorCode.RECEIPT_WRITEOFF_EXCEED: 422,
    FINErrorCode.RECEIPT_INVALID_TRANSITION: 422,
    FINErrorCode.RECEIPT_AMOUNT_MISMATCH: 422,
    FINErrorCode.INVOICE_AMOUNT_MISMATCH: 422,
    FINErrorCode.INVOICE_RED_INVALID: 422,
    FINErrorCode.INVOICE_VERIFY_FAIL: 422,
    FINErrorCode.INVOICE_LINE_AMOUNT_MISMATCH: 422,
    FINErrorCode.INVOICE_VOID_REASON_REQUIRED: 422,
    FINErrorCode.RECON_WRITEOFF_NO_EVIDENCE: 422,
    FINErrorCode.RECON_INVALID_TRANSITION: 422,
    FINErrorCode.RECON_PERIOD_OVERLAP: 422,
    FINErrorCode.GL_UNBALANCED: 422,
    FINErrorCode.GL_PERIOD_UNBALANCED: 422,
    FINErrorCode.TREASURY_INSUFFICIENT_BALANCE: 422,
    FINErrorCode.TREASURY_TRANSFER_SAME_ACCOUNT: 422,
    FINErrorCode.TREASURY_TRANSFER_INVALID_TRANSITION: 422,
    FINErrorCode.TREASURY_FREEZE_EXCEED: 422,
    FINErrorCode.SETTLEMENT_CROSS_TENANT_NOT_CONFIRMED: 422,
    FINErrorCode.SETTLEMENT_CANCEL_WITH_PAYMENT: 422,
    FINErrorCode.VOUCHER_RED_AMOUNT_EXCEED: 422,
    # 423 Locked - 期间锁定/核心冻结
    FINErrorCode.CORE_FREEZE_VIOLATION: 423,
    FINErrorCode.GL_PERIOD_CLOSED: 423,
    # 500 Internal
    FINErrorCode.INTERNAL_ERROR: 500,
    # 502 Bad Gateway - 外部依赖失败
    FINErrorCode.PAYMENT_ACCOUNT_ENCRYPT_FAIL: 502,
    FINErrorCode.TREASURY_TRANSFER_FAILED: 502,
    FINErrorCode.RECEIPT_NO_EVIDENCE: 502,
}


class FINErrorCodeTest:
    """FINErrorCode 枚举完整性与前缀测试。"""

    def test_all_codes_classified(self) -> None:
        all_codes = set(FINErrorCode)
        classified = set(_EXPECTED_STATUS)
        assert classified == all_codes

    def test_total_code_count_is_76(self) -> None:
        # 实际定义 76 个错误码
        assert len(list(FINErrorCode)) == 76
        assert len(_EXPECTED_STATUS) == 76

    def test_all_codes_carry_eitp_fin_prefix(self) -> None:
        for code in FINErrorCode:
            assert code.value.startswith("EITP_FIN_"), f"{code} 前缀不符"

    def test_codes_are_unique(self) -> None:
        values = [c.value for c in FINErrorCode]
        assert len(values) == len(set(values))

    def test_enum_is_str_enum(self) -> None:
        for code in FINErrorCode:
            assert isinstance(code, str)
            assert code.value == code


class FINHttpStatusMappingTest:
    """_status_for_fin_code HTTP 状态码映射测试。"""

    def test_every_code_maps_to_expected_status(self) -> None:
        for code, expected in _EXPECTED_STATUS.items():
            assert _status_for_fin_code(code) == expected, f"{code} 映射不符"

    def test_status_for_code_dispatches_fin_error_code(self) -> None:
        # _status_for_code 通过 isinstance 分发，校验的是 middleware 内部 FINErrorCode
        # （error_handler.py 中重复定义的枚举），而非 domain FINErrorCode。
        # 此处用 middleware 枚举验证真实生产分发路径。
        assert _status_for_code(MiddlewareFINErrorCode.SETTLEMENT_NOT_FOUND) == 404
        assert _status_for_code(MiddlewareFINErrorCode.INVOICE_ARCHIVED_IMMUTABLE) == 403
        assert _status_for_code(MiddlewareFINErrorCode.SETTLEMENT_DUPLICATE) == 409
        assert _status_for_code(MiddlewareFINErrorCode.MONEY_FLOAT_FORBIDDEN) == 422
        assert _status_for_code(MiddlewareFINErrorCode.GL_PERIOD_CLOSED) == 423
        assert _status_for_code(MiddlewareFINErrorCode.INTERNAL_ERROR) == 500
        assert _status_for_code(MiddlewareFINErrorCode.TREASURY_TRANSFER_FAILED) == 502

    def test_domain_fin_error_code_not_dispatched_by_status_for_code(self) -> None:
        # domain FINErrorCode 与 middleware FINErrorCode 是不同类，
        # isinstance 分发不命中，落入默认 400。此为已知架构现状。
        assert _status_for_code(FINErrorCode.SETTLEMENT_NOT_FOUND) == 400

    def test_status_distribution_counts(self) -> None:
        counts = Counter(_status_for_fin_code(c) for c in FINErrorCode)
        assert counts[403] == 7
        assert counts[404] == 14
        assert counts[409] == 14
        assert counts[422] == 35
        assert counts[423] == 2
        assert counts[500] == 1
        assert counts[502] == 3
        # 无任何 code 落入默认 400
        assert counts.get(400, 0) == 0

    def test_all_codes_covered_no_default_400(self) -> None:
        # 确保没有错误码落入兜底 400
        for code in FINErrorCode:
            assert _status_for_fin_code(code) != 400, f"{code} 未分类"


class FINErrorTest:
    """FINError 异常构造与属性测试。"""

    def test_construct_with_code_and_message(self) -> None:
        err = FINError(FINErrorCode.SETTLEMENT_NOT_FOUND, "结算单不存在")
        assert err.code == FINErrorCode.SETTLEMENT_NOT_FOUND
        assert err.message == "结算单不存在"
        assert err.details == {}

    def test_construct_with_details(self) -> None:
        err = FINError(
            FINErrorCode.AR_UNBALANCED,
            "应收不平衡",
            details={"receivable": 1000, "received": 300},
        )
        assert err.details == {"receivable": 1000, "received": 300}

    def test_details_default_is_empty_dict_when_none(self) -> None:
        err = FINError(FINErrorCode.MONEY_FLOAT_FORBIDDEN, "x", details=None)
        assert err.details == {}

    def test_is_exception_subclass(self) -> None:
        err = FINError(FINErrorCode.INTERNAL_ERROR, "内部错误")
        assert isinstance(err, Exception)

    def test_raise_and_catch_code(self) -> None:
        with pytest.raises(FINError) as exc:
            raise FINError(FINErrorCode.PAYMENT_INVALID_TRANSITION, "非法状态转换")
        assert exc.value.code == FINErrorCode.PAYMENT_INVALID_TRANSITION
        assert "非法状态转换" in str(exc.value)

    def test_fin_error_not_same_as_domain_error(self) -> None:
        # FINError 是领域独立异常基类，不继承 middleware DomainError
        err = FINError(FINErrorCode.INTERNAL_ERROR, "x")
        assert not isinstance(err, DomainError)