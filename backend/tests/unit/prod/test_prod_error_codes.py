"""PROD 错误码与 HTTP 状态码映射单元测试 - PRODErrorCode(64) → _status_for_prod_code。

覆盖 domain/prod/error_codes.py 的 PRODErrorCode 唯一性/前缀/计数、
error_handler._status_for_prod_code 对每个 code 的 HTTP 状态分发、
领域层与中间件层枚举值集合一致性、关键 code 的具体状态码
（403/404/409/422/423/500/502/503/504）、状态分发覆盖全部 64 个码。
"""

from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# 领域层 PRODErrorCode（被测对象之一）
from app.domain.prod.error_codes import PRODErrorCode as DomainPRODErrorCode

# 中间件层 PRODErrorCode 与状态映射（_status_for_prod_code 接受此类）
from app.interfaces.middleware.error_handler import (
    PRODErrorCode as MiddlewarePRODErrorCode,
    _status_for_prod_code,
)


# 期望的关键 code → HTTP 状态码（覆盖各分类代表）
_EXPECTED_KEY_STATUS = {
    MiddlewarePRODErrorCode.CORE_FREEZE_VIOLATED: 403,
    MiddlewarePRODErrorCode.VERIFICATION_NOT_FOUND: 404,
    MiddlewarePRODErrorCode.VERIFICATION_ALREADY_RUNNING: 409,
    MiddlewarePRODErrorCode.VERIFICATION_PREREQUISITE_NOT_MET: 422,
    MiddlewarePRODErrorCode.DOSSIER_EVIDENCE_TAMPERED: 423,
    MiddlewarePRODErrorCode.INTERNAL_ERROR: 500,
    MiddlewarePRODErrorCode.DR_API_UNAVAILABLE: 502,
    MiddlewarePRODErrorCode.CONNPOOL_EXHAUSTED_NO_TIMEOUT: 503,
    MiddlewarePRODErrorCode.JOB_SCHEDULE_DRIFT: 504,
}


class PRODErrorCodeTest:
    """PRODErrorCode 枚举完整性测试。"""

    def test_domain_prod_error_code_has_64_unique_values(self) -> None:
        values = [c.value for c in DomainPRODErrorCode]
        assert len(values) == 64
        assert len(values) == len(set(values)), "存在重复错误码"

    def test_all_codes_carry_eitp_prod_prefix(self) -> None:
        for code in DomainPRODErrorCode:
            assert code.value.startswith("EITP_PROD_"), f"{code} 前缀不符"

    def test_domain_and_middleware_enums_are_value_aligned(self) -> None:
        # 两个 PRODErrorCode 的值集合应完全一致，保证领域层与中间件层错误码同步
        domain_values = {c.value for c in DomainPRODErrorCode}
        middleware_values = {c.value for c in MiddlewarePRODErrorCode}
        assert domain_values == middleware_values

    def test_status_for_prod_code_maps_to_valid_http_status(self) -> None:
        valid_statuses = {400, 403, 404, 409, 422, 423, 500, 502, 503, 504}
        for code in MiddlewarePRODErrorCode:
            status = _status_for_prod_code(code)
            assert status in valid_statuses, f"{code} 映射到非预期状态 {status}"

    def test_key_codes_map_to_expected_status(self) -> None:
        for code, expected in _EXPECTED_KEY_STATUS.items():
            assert _status_for_prod_code(code) == expected, f"{code} 映射不符"

    def test_status_distribution_covers_all_codes(self) -> None:
        # 每个错误码都应被某个分类命中，分发总数应等于枚举总数
        counts = Counter(_status_for_prod_code(c) for c in MiddlewarePRODErrorCode)
        assert sum(counts.values()) == 64
        # 至少命中多个不同状态分类，证明映射非退化
        assert len(counts) >= 7