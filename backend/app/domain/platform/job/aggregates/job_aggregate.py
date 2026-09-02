"""Job 定义与执行聚合根。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class JobStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class ConcurrencyStrategy(str, Enum):
    ALLOW = "ALLOW"
    FORBID = "FORBID"
    QUEUE = "QUEUE"


class TenantScope(str, Enum):
    ALL = "ALL"
    SPECIFIED = "SPECIFIED"
    PLATFORM = "PLATFORM"


@dataclass(frozen=True)
class JobDefinitionAggregate:
    """Job 定义聚合根 - 定时任务配置。"""

    job_id: UUID
    job_name: str
    cron_expression: str
    handler_ref: str
    timeout_seconds: int
    retry_policy: dict
    concurrency_strategy: str
    tenant_scope: str
    enabled: bool
    next_run_at: datetime | None
    tenant_id: UUID | None

    @classmethod
    def create(
        cls,
        job_name: str,
        cron_expression: str,
        handler_ref: str,
        timeout_seconds: int = 300,
        retry_policy: dict | None = None,
        concurrency_strategy: str = ConcurrencyStrategy.FORBID.value,
        tenant_scope: str = TenantScope.PLATFORM.value,
        tenant_id: UUID | None = None,
    ) -> JobDefinitionAggregate:
        return cls(
            job_id=uuid4(),
            job_name=job_name,
            cron_expression=cron_expression,
            handler_ref=handler_ref,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy or {"max_retries": 3, "backoff_seconds": 5},
            concurrency_strategy=concurrency_strategy,
            tenant_scope=tenant_scope,
            enabled=False,
            next_run_at=None,
            tenant_id=tenant_id,
        )

    def enable(self) -> JobDefinitionAggregate:
        from dataclasses import replace
        return replace(self, enabled=True)

    def disable(self) -> JobDefinitionAggregate:
        from dataclasses import replace
        return replace(self, enabled=False)


@dataclass(frozen=True)
class JobExecutionAggregate:
    """Job 执行聚合根 - 执行记录。"""

    execution_id: UUID
    job_id: UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    error_message: str | None
    tenant_id: UUID | None

    @classmethod
    def start(cls, job_id: UUID, tenant_id: UUID | None = None) -> JobExecutionAggregate:
        return cls(
            execution_id=uuid4(),
            job_id=job_id,
            status=JobStatus.RUNNING.value,
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            duration_ms=None,
            error_message=None,
            tenant_id=tenant_id,
        )

    def succeed(self, duration_ms: int) -> JobExecutionAggregate:
        from dataclasses import replace
        return replace(
            self,
            status=JobStatus.SUCCESS.value,
            finished_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
        )

    def fail(self, error_message: str, duration_ms: int) -> JobExecutionAggregate:
        from dataclasses import replace
        return replace(
            self,
            status=JobStatus.FAILED.value,
            finished_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            error_message=error_message,
        )

    def timeout(self, duration_ms: int) -> JobExecutionAggregate:
        from dataclasses import replace
        return replace(
            self,
            status=JobStatus.TIMEOUT.value,
            finished_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            error_message="Job execution timed out",
        )