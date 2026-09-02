"""统一错误响应信封。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ErrorEnvelope(BaseModel):
    """统一错误响应信封 - 所有 API 错误返回统一格式。"""

    error_code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    trace_id: str | None = Field(None, description="追踪 ID")
    request_id: str | None = Field(None, description="请求 ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="时间戳")
    details: dict[str, Any] = Field(default_factory=dict, description="附加详情")
    http_status: int = Field(..., description="HTTP 状态码")

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        http_status: int,
        trace_id: str | None = None,
        request_id: str | None = None,
        error_code: str | None = None,
        message: str | None = None,
        details: dict | None = None,
    ) -> ErrorEnvelope:
        from app.domain.platform.exceptions import PLTError

        if isinstance(exc, PLTError):
            return cls(
                error_code=exc.code.value,
                message=exc.message,
                trace_id=trace_id,
                request_id=request_id or str(uuid4()),
                details=exc.details,
                http_status=http_status,
            )
        return cls(
            error_code=error_code or "EITP_PLT_INTERNAL_ERROR",
            message=message or str(exc) or "内部服务器错误",
            trace_id=trace_id,
            request_id=request_id or str(uuid4()),
            details=details or {},
            http_status=http_status,
        )