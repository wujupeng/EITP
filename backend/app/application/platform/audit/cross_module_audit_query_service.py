"""跨模块审计查询服务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from structlog import get_logger

logger = get_logger(__name__)


class CrossModuleAuditQueryService:
    """跨模块审计查询服务 - 多维度检索，复合索引优化。"""

    def __init__(self, repository: Any) -> None:
        self._repository = repository

    async def query(
        self,
        tenant_id: UUID | None = None,
        module: str | None = None,
        operation_type: str | None = None,
        operator_id: str | None = None,
        aggregate_root_type: str | None = None,
        aggregate_root_id: str | None = None,
        trace_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        return await self._repository.query_multi_dim(
            tenant_id=tenant_id,
            module=module,
            operation_type=operation_type,
            operator_id=operator_id,
            aggregate_root_type=aggregate_root_type,
            aggregate_root_id=aggregate_root_id,
            trace_id=trace_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    async def query_by_trace_id(self, trace_id: str, tenant_id: UUID | None = None) -> list[dict]:
        return await self._repository.query_multi_dim(
            tenant_id=tenant_id,
            trace_id=trace_id,
            limit=1000,
        )

    async def query_by_aggregate(
        self,
        tenant_id: UUID,
        aggregate_root_type: str,
        aggregate_root_id: str,
        limit: int = 100,
    ) -> list[dict]:
        return await self._repository.query_multi_dim(
            tenant_id=tenant_id,
            aggregate_root_type=aggregate_root_type,
            aggregate_root_id=aggregate_root_id,
            limit=limit,
        )

    async def query_by_time_range(
        self,
        tenant_id: UUID,
        start_time: datetime,
        end_time: datetime,
        module: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return await self._repository.query_multi_dim(
            tenant_id=tenant_id,
            module=module,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )