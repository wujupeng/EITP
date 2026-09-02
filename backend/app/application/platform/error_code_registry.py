"""错误码注册表 - 统一管理 9 套错误码枚举。"""

from __future__ import annotations

from enum import Enum
from typing import Type

from structlog import get_logger

from app.domain.platform.error_codes import PLTErrorCode
from app.domain.platform.exceptions import PLTError
from app.interfaces.middleware.error_handler import (
    ErrorCode,
    IAMErrorCode,
    INVErrorCode,
    MDMErrorCode,
    WMSErrorCode,
    PURErrorCode,
    SALErrorCode,
    SECErrorCode,
)

logger = get_logger(__name__)

_ALL_ENUMS: list[Type[Enum]] = [
    ErrorCode,
    IAMErrorCode,
    INVErrorCode,
    MDMErrorCode,
    WMSErrorCode,
    PURErrorCode,
    SALErrorCode,
    SECErrorCode,
    PLTErrorCode,
]


class ErrorCodeRegistry:
    """错误码注册表 - 注册 9 套枚举，禁止重复注册。"""

    def __init__(self) -> None:
        self._code_to_enum: dict[str, Enum] = {}
        self._code_to_http: dict[str, int] = {}

    def register(self, enum_cls: Type[Enum]) -> None:
        for member in enum_cls:
            value = member.value if isinstance(member.value, str) else str(member.value)
            if value in self._code_to_enum:
                logger.error("errorcode_duplicate", code=value, existing=self._code_to_enum[value])
                raise PLTError(PLTErrorCode.ERRORCODE_DUPLICATE, f"错误码重复注册: {value}")
            self._code_to_enum[value] = member

    def register_all(self) -> None:
        for enum_cls in _ALL_ENUMS:
            self.register(enum_cls)

    def is_registered(self, code: str) -> bool:
        return code in self._code_to_enum

    def resolve(self, code: str) -> Enum | None:
        if code not in self._code_to_enum:
            logger.warning("errorcode_not_registered", code=code)
            return None
        return self._code_to_enum[code]

    def resolve_or_default(self, code: str) -> tuple[str, int]:
        member = self._code_to_enum.get(code)
        if member is None:
            return PLTErrorCode.ERRORCODE_NOT_REGISTERED.value, 500
        return code, 500


_registry: ErrorCodeRegistry | None = None


def get_registry() -> ErrorCodeRegistry:
    global _registry
    if _registry is None:
        _registry = ErrorCodeRegistry()
        _registry.register_all()
    return _registry