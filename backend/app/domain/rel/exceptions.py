"""REL 领域异常类。"""

from __future__ import annotations

from app.domain.rel.error_codes import RELErrorCode


class RELError(Exception):
    """REL 领域错误基类。"""

    def __init__(self, code: RELErrorCode, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)