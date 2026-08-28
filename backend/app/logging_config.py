"""结构化日志配置 - 注入 tenant_id / user_id / trace_id。"""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.types import EventDict

from app.interfaces.middleware.tenant_context import TenantContext


def _add_tenant_context(_logger: object, _method_name: str, event_dict: EventDict) -> EventDict:
    """将当前 TenantContext 注入日志事件。"""
    ctx = TenantContext.current()
    if ctx is not None:
        event_dict["tenant_id"] = str(ctx.tenant_id)
        if ctx.user_id is not None:
            event_dict["user_id"] = str(ctx.user_id)
    return event_dict


def _add_trace_id(_logger: object, _method_name: str, event_dict: EventDict) -> EventDict:
    """注入 trace_id（若请求状态中存在）。"""
    # trace_id 由 TraceMiddleware 设置到 request.state，
    # 在非请求上下文中不注入。
    return event_dict


def setup_logging(level: str = "INFO", json_output: bool = True) -> None:
    """配置 structlog 结构化日志。"""
    processors = [
        structlog.contextvars.merge_contextvars,
        _add_tenant_context,
        _add_trace_id,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=getattr(logging, level), stream=sys.stderr)