"""链路追踪中间件 - 注入 trace_id / tenant_id / user_id 到结构化日志。"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.interfaces.middleware.tenant_context import TenantContext


class TraceMiddleware(BaseHTTPMiddleware):
    """链路追踪中间件 - 为每个请求生成 trace_id 并注入响应头。"""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id

        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id

        ctx = TenantContext.current()
        if ctx is not None:
            response.headers["X-Tenant-ID"] = str(ctx.tenant_id)

        return response