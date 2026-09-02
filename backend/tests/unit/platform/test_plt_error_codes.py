"""PLT 错误码与 HTTP 状态码映射单元测试 - PLTErrorCode(64) → _status_for_plt_code。

覆盖 platform/error_codes.py 的 PLTErrorCode 唯一性/前缀/计数、
error_handler._status_for_plt_code 对每个 code 的 HTTP 状态分发、
两枚举值集合一致性、关键 code 的具体状态码（405/423/429/503/504/409）、
PLTError 异常构造与抛出。
"""

from __future__ import annotations

import os
import sys
from collections import Counter

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# 领域层 PLTErrorCode（被测对象之一）
from app.domain.platform.error_codes import PLTErrorCode as DomainPLTErrorCode
from app.domain.platform.exceptions import PLTError as DomainPLTError

# 中间件层 PLTErrorCode 与状态映射（_status_for_plt_code 接受此类）
from app.interfaces.middleware.error_handler import (
    DomainError,
    PLTError,
    PLTErrorCode as MiddlewarePLTErrorCode,
    _status_for_code,
    _status_for_plt_code,
)


# 期望的关键 code → HTTP 状态码（覆盖各分类代表）
_EXPECTED_KEY_STATUS = {
    MiddlewarePLTErrorCode.AUDIT_UPDATE_FORBIDDEN: 405,
    MiddlewarePLTErrorCode.AUDIT_DELETE_FORBIDDEN: 405,
    MiddlewarePLTErrorCode.AUDIT_TAMPER_DETECTED: 423,
    MiddlewarePLTErrorCode.AUDIT_HASH_CHAIN_BROKEN: 423,
    MiddlewarePLTErrorCode.RATE_LIMIT_EXCEEDED: 429,
    MiddlewarePLTErrorCode.DB_UNAVAILABLE: 503,
    MiddlewarePLTErrorCode.UPSTREAM_TIMEOUT: 504,
    MiddlewarePLTErrorCode.IDEMPOTENCY_CONFLICT: 409,
    MiddlewarePLTErrorCode.AUDIT_NOT_FOUND: 404,
    MiddlewarePLTErrorCode.AUDIT_CROSS_TENANT_DENIED: 403,
    MiddlewarePLTErrorCode.API_VERSION_SUNSET: 410,
    MiddlewarePLTErrorCode.UPSTREAM_UNAVAILABLE: 502,
    MiddlewarePLTErrorCode.INTERNAL_ERROR: 500,
    MiddlewarePLTErrorCode.OUTBOX_ALREADY_DELIVERED: 400,
}


class PLTErrorCodeTest:
    """PLTErrorCode 枚举完整性测试。"""

    def test_domain_plt_error_code_has_64_unique_values(self) -> None:
        values = [c.value for c in DomainPLTErrorCode]
        assert len(values) == 64
        assert len(values) == len(set(values)), "存在重复错误码"

    def test_middleware_plt_error_code_has_64_unique_values(self) -> None:
        values = [c.value for c in MiddlewarePLTErrorCode]
        assert len(values) == 64
        assert len(values) == len(set(values))

    def test_all_codes_carry_eitp_plt_prefix(self) -> None:
        for code in DomainPLTErrorCode:
            assert code.value.startswith("EITP_PLT_"), f"{code} 前缀不符"

    def test_domain_and_middleware_enums_are_value_aligned(self) -> None:
        # 两个 PLTErrorCode 的值集合应完全一致，保证领域层与中间件层错误码同步
        domain_values = {c.value for c in DomainPLTErrorCode}
        middleware_values = {c.value for c in MiddlewarePLTErrorCode}
        assert domain_values == middleware_values


class StatusForPltCodeTest:
    """_status_for_plt_code HTTP 状态码映射测试。"""

    def test_every_code_maps_to_valid_http_status(self) -> None:
        valid_statuses = {400, 403, 404, 405, 409, 410, 422, 423, 429, 500, 502, 503, 504}
        for code in MiddlewarePLTErrorCode:
            status = _status_for_plt_code(code)
            assert status in valid_statuses, f"{code} 映射到非预期状态 {status}"

    def test_key_codes_map_to_expected_status(self) -> None:
        for code, expected in _EXPECTED_KEY_STATUS.items():
            assert _status_for_plt_code(code) == expected, f"{code} 映射不符"

    def test_audit_update_forbidden_maps_to_405(self) -> None:
        assert _status_for_plt_code(MiddlewarePLTErrorCode.AUDIT_UPDATE_FORBIDDEN) == 405

    def test_audit_tamper_detected_maps_to_423(self) -> None:
        assert _status_for_plt_code(MiddlewarePLTErrorCode.AUDIT_TAMPER_DETECTED) == 423

    def test_rate_limit_exceeded_maps_to_429(self) -> None:
        assert _status_for_plt_code(MiddlewarePLTErrorCode.RATE_LIMIT_EXCEEDED) == 429

    def test_db_unavailable_maps_to_503(self) -> None:
        assert _status_for_plt_code(MiddlewarePLTErrorCode.DB_UNAVAILABLE) == 503

    def test_upstream_timeout_maps_to_504(self) -> None:
        assert _status_for_plt_code(MiddlewarePLTErrorCode.UPSTREAM_TIMEOUT) == 504

    def test_idempotency_conflict_maps_to_409(self) -> None:
        assert _status_for_plt_code(MiddlewarePLTErrorCode.IDEMPOTENCY_CONFLICT) == 409

    def test_status_for_code_dispatches_plt_error_code(self) -> None:
        # _status_for_code 应识别 PLTErrorCode 并走 PLT 分支
        assert _status_for_code(MiddlewarePLTErrorCode.AUDIT_TAMPER_DETECTED) == 423
        assert _status_for_code(MiddlewarePLTErrorCode.RATE_LIMIT_EXCEEDED) == 429

    def test_status_distribution_covers_all_codes(self) -> None:
        # 每个错误码都应被某个分类命中，不应落入默认 400 兜底以外的未覆盖情形
        counts = Counter(_status_for_plt_code(c) for c in MiddlewarePLTErrorCode)
        assert sum(counts.values()) == 64


class PLTErrorTest:
    """PLTError 异常构造与继承测试。"""

    def test_domain_plt_error_construct_and_raise(self) -> None:
        with pytest.raises(DomainPLTError) as exc:
            raise DomainPLTError(DomainPLTErrorCode.TENANT_INVALID_TRANSITION, "非法状态转换")
        assert exc.value.code == DomainPLTErrorCode.TENANT_INVALID_TRANSITION
        assert exc.value.message == "非法状态转换"
        assert exc.value.details == {}

    def test_domain_plt_error_with_details(self) -> None:
        err = DomainPLTError(DomainPLTErrorCode.TENANT_QUOTA_EXCEEDED, "超限", details={"limit": 100})
        assert err.details == {"limit": 100}

    def test_middleware_plt_error_is_domain_error_subclass(self) -> None:
        err = PLTError(MiddlewarePLTErrorCode.INTERNAL_ERROR, "内部错误")
        assert isinstance(err, DomainError)
        assert isinstance(err, Exception)