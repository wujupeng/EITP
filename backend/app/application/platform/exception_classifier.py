"""异常分类器 - 按异常类型分类为业务异常/系统异常/外部依赖异常。"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.platform.error_codes import PLTErrorCode


@dataclass(frozen=True)
class ClassifiedError:
    """分类后的异常。"""

    category: str
    http_status: int
    error_code: str
    message: str


class ExceptionClassifier:
    """异常分类器 - 将异常分类为业务异常(4xx)/系统异常(5xx)/外部依赖异常(502/503/504)。"""

    BUSINESS_EXCEPTIONS = (
        ValueError,
        KeyError,
        AttributeError,
        TypeError,
    )

    DB_EXCEPTION_NAMES = {
        "OperationalError",
        "ConnectionRefusedError",
        "ConnectionResetError",
        "TimeoutError",
        "AsyncAdapt_asyncpg_dbapi",
    }

    TIMEOUT_EXCEPTION_NAMES = {
        "TimeoutError",
        "asyncio.TimeoutError",
        "TimeoutError",
    }

    @classmethod
    def classify(cls, exc: Exception) -> ClassifiedError:
        exc_name = type(exc).__name__

        if exc_name in cls.TIMEOUT_EXCEPTION_NAMES or "timeout" in str(exc).lower():
            return ClassifiedError(
                category="external",
                http_status=504,
                error_code=PLTErrorCode.UPSTREAM_TIMEOUT.value,
                message=f"上游服务超时: {exc}",
            )

        if exc_name in cls.DB_EXCEPTION_NAMES or "connection" in str(exc).lower():
            return ClassifiedError(
                category="external",
                http_status=503,
                error_code=PLTErrorCode.DB_UNAVAILABLE.value,
                message=f"数据库不可用: {exc}",
            )

        if "unavailable" in str(exc).lower() or "unreachable" in str(exc).lower():
            return ClassifiedError(
                category="external",
                http_status=502,
                error_code=PLTErrorCode.UPSTREAM_UNAVAILABLE.value,
                message=f"上游服务不可用: {exc}",
            )

        if isinstance(exc, cls.BUSINESS_EXCEPTIONS):
            return ClassifiedError(
                category="business",
                http_status=422,
                error_code=PLTErrorCode.INTERNAL_ERROR.value,
                message=str(exc) or "业务校验失败",
            )

        return ClassifiedError(
            category="system",
            http_status=500,
            error_code=PLTErrorCode.INTERNAL_ERROR.value,
            message=str(exc) or "内部服务器错误",
        )