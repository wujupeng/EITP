"""FIN 领域异常类。"""

from __future__ import annotations

from app.domain.fin.error_codes import FINErrorCode


class FINError(Exception):
    """FIN 财务领域错误基类。"""

    def __init__(self, code: FINErrorCode, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)