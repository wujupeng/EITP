"""PLT 领域异常类。"""

from __future__ import annotations

from app.domain.platform.error_codes import PLTErrorCode


class PLTError(Exception):
    """PLT 领域错误基类。"""

    def __init__(self, code: PLTErrorCode, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)