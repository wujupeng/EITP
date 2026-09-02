"""PROD 领域异常类。"""

from __future__ import annotations

from app.domain.prod.error_codes import PRODErrorCode


class PRODError(Exception):
    """PROD 领域错误基类。"""

    def __init__(self, code: PRODErrorCode, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)