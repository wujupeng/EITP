"""REL 领域异常单元测试 - RELError 基类构造 / code / message / details。

覆盖 domain/rel/exceptions.py 的 RELError 构造、默认 details、
code/message/details 属性、Exception 继承。
"""

from __future__ import annotations

import pytest

from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


class RELErrorTest:
    """RELError 领域异常基类测试。"""

    def test_construct_with_code_and_message(self) -> None:
        err = RELError(RELErrorCode.INTERNAL_ERROR, "boom")
        assert err.code == RELErrorCode.INTERNAL_ERROR
        assert err.message == "boom"
        assert err.details == {}

    def test_construct_with_details(self) -> None:
        err = RELError(
            RELErrorCode.SEAL_INVALID_STATE_TRANSITION,
            "bad transition",
            {"from": "SEALED", "to": "REQUESTED"},
        )
        assert err.details == {"from": "SEALED", "to": "REQUESTED"}

    def test_details_defaults_to_empty_dict_when_none(self) -> None:
        err = RELError(RELErrorCode.SEAL_FAIL, "fail", None)
        assert err.details == {}

    def test_is_subclass_of_exception(self) -> None:
        assert issubclass(RELError, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(RELError) as exc:
            raise RELError(RELErrorCode.SEAL_NOT_FOUND, "missing")
        assert exc.value.code == RELErrorCode.SEAL_NOT_FOUND
        assert str(exc.value) == "missing"

    def test_details_is_independent_per_instance(self) -> None:
        err1 = RELError(RELErrorCode.INTERNAL_ERROR, "a")
        err2 = RELError(RELErrorCode.INTERNAL_ERROR, "b")
        err1.details["k"] = "v"
        assert err2.details == {}