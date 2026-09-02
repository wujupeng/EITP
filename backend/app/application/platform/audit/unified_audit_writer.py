"""统一审计写入器 - 异步写入 + 降级策略 + 装饰器。"""

from __future__ import annotations

import asyncio
import functools
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from structlog import get_logger

from app.domain.platform.audit.aggregates.audit_record_aggregate import AuditRecordAggregate

logger = get_logger(__name__)

_fallback_buffer: asyncio.Queue = asyncio.Queue()


class UnifiedAuditWriter:
    """统一审计写入器 - 异步写入，不阻塞业务主路径。"""

    def __init__(self, repository_factory: Callable | None = None) -> None:
        self._repository_factory = repository_factory
        self._buffer = _fallback_buffer

    async def write(
        self,
        tenant_id: UUID,
        module: str,
        aggregate_root_type: str,
        aggregate_root_id: str,
        operation_type: str,
        operator_id: str,
        trace_id: str,
        prev_hash: str,
        before_snapshot: dict | None = None,
        after_snapshot: dict | None = None,
        retention_days: int = 365,
    ) -> AuditRecordAggregate | None:
        retention_until = datetime.now(timezone.utc) + timedelta(days=retention_days)
        record = AuditRecordAggregate.create(
            tenant_id=tenant_id,
            module=module,
            aggregate_root_type=aggregate_root_type,
            aggregate_root_id=aggregate_root_id,
            operation_type=operation_type,
            operator_id=operator_id,
            trace_id=trace_id,
            prev_hash=prev_hash,
            retention_until=retention_until,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

        if self._repository_factory is None:
            await self._buffer.put(record)
            logger.debug("audit_buffered", audit_id=str(record.audit_id))
            return record

        try:
            repo = self._repository_factory()
            await repo.save(record)
            logger.debug("audit_written", audit_id=str(record.audit_id))
        except Exception as exc:
            await self._buffer.put(record)
            logger.warning("audit_write_failed_buffered", error=str(exc))
        return record

    async def flush_buffer(self) -> int:
        if self._repository_factory is None:
            return 0
        count = 0
        while not self._buffer.empty():
            record = await self._buffer.get()
            try:
                repo = self._repository_factory()
                await repo.save(record)
                count += 1
            except Exception as exc:
                await self._buffer.put(record)
                logger.error("audit_flush_failed", error=str(exc))
                break
        return count


def audit_write(module: str, action: str) -> Callable:
    """审计写入装饰器 - 应用于应用服务方法。"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            try:
                writer = _get_global_writer()
                if writer is not None:
                    tenant_id = kwargs.get("tenant_id") or (args[0] if args else None)
                    operator_id = kwargs.get("operator_id", "system")
                    trace_id = kwargs.get("trace_id", "")
                    aggregate_root_type = getattr(result, "__class__", type(result)).__name__
                    aggregate_root_id = str(getattr(result, "id", getattr(result, "aggregate_id", "")))
                    await writer.write(
                        tenant_id=tenant_id,
                        module=module,
                        aggregate_root_type=aggregate_root_type,
                        aggregate_root_id=aggregate_root_id,
                        operation_type=action,
                        operator_id=operator_id,
                        trace_id=trace_id,
                        prev_hash="",
                    )
            except Exception as exc:
                logger.warning("audit_decorator_failed", error=str(exc))
            return result

        return wrapper

    return decorator


_global_writer: UnifiedAuditWriter | None = None


def _get_global_writer() -> UnifiedAuditWriter | None:
    return _global_writer


def set_global_writer(writer: UnifiedAuditWriter) -> None:
    global _global_writer
    _global_writer = writer