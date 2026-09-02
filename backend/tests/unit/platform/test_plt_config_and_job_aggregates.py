"""PLT ConfigRevisionAggregate / JobDefinitionAggregate / JobExecutionAggregate 单元测试。

覆盖 ConfigRevisionAggregate.create()、is_secret()/is_gray_release() 判定；
JobDefinitionAggregate.create() 默认 enabled=False、enable()/disable() 切换；
JobExecutionAggregate.start() RUNNING、succeed()/fail()/timeout() 终态流转。
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.domain.platform.config.aggregates.config_revision_aggregate import (
    ConfigRevisionAggregate,
    ConfigValueType,
)
from app.domain.platform.job.aggregates.job_aggregate import (
    ConcurrencyStrategy,
    JobDefinitionAggregate,
    JobExecutionAggregate,
    JobStatus,
    TenantScope,
)


class ConfigRevisionAggregateTest:
    """ConfigRevisionAggregate 配置版本测试。"""

    def test_create_sets_default_version_and_namespace(self) -> None:
        rev = ConfigRevisionAggregate.create(
            namespace="GLOBAL",
            config_key="max_connections",
            config_value={"v": 100},
            value_type=ConfigValueType.INT.value,
            description="最大连接数",
            changed_by="admin",
        )
        assert rev.version == 1
        assert rev.namespace == "GLOBAL"
        assert rev.namespace_id is None
        assert rev.gray_release_config is None
        assert rev.value_range is None

    def test_is_secret_returns_true_for_secret_type(self) -> None:
        rev = ConfigRevisionAggregate.create(
            namespace="TENANT",
            config_key="db_password",
            config_value={"v": "***"},
            value_type=ConfigValueType.SECRET.value,
            description="数据库密码",
            changed_by="admin",
        )
        assert rev.is_secret() is True

    def test_is_secret_returns_false_for_non_secret_type(self) -> None:
        rev = ConfigRevisionAggregate.create(
            namespace="GLOBAL",
            config_key="timeout",
            config_value={"v": 30},
            value_type=ConfigValueType.INT.value,
            description="超时",
            changed_by="admin",
        )
        assert rev.is_secret() is False

    def test_is_gray_release_true_when_gray_release_config_set(self) -> None:
        rev = ConfigRevisionAggregate.create(
            namespace="MODULE",
            config_key="new_feature_flag",
            config_value={"v": True},
            value_type=ConfigValueType.BOOL.value,
            description="灰度开关",
            changed_by="admin",
            gray_release_config={"tenant_ids": ["t-1", "t-2"], "percentage": 10},
        )
        assert rev.is_gray_release() is True

    def test_is_gray_release_false_when_gray_release_config_none(self) -> None:
        rev = ConfigRevisionAggregate.create(
            namespace="GLOBAL",
            config_key="k",
            config_value={"v": 1},
            value_type=ConfigValueType.INT.value,
            description="d",
            changed_by="admin",
        )
        assert rev.is_gray_release() is False


class JobDefinitionAggregateTest:
    """JobDefinitionAggregate 定时任务定义测试。"""

    def test_create_sets_enabled_false_and_defaults(self) -> None:
        job = JobDefinitionAggregate.create(
            job_name="daily-settlement",
            cron_expression="0 2 * * *",
            handler_ref="app.jobs.settlement:run",
        )
        assert job.enabled is False
        assert job.next_run_at is None
        assert job.concurrency_strategy == ConcurrencyStrategy.FORBID.value
        assert job.tenant_scope == TenantScope.PLATFORM.value
        assert job.timeout_seconds == 300
        assert job.retry_policy == {"max_retries": 3, "backoff_seconds": 5}

    def test_enable_sets_enabled_true(self) -> None:
        job = JobDefinitionAggregate.create("j", "* * * * *", "h:run")
        enabled = job.enable()
        assert enabled.enabled is True
        assert job.enabled is False  # 原实例不变

    def test_disable_sets_enabled_false(self) -> None:
        job = JobDefinitionAggregate.create("j", "* * * * *", "h:run").enable()
        disabled = job.disable()
        assert disabled.enabled is False
        assert job.enabled is True

    def test_enable_disable_roundtrip(self) -> None:
        job = JobDefinitionAggregate.create("j", "* * * * *", "h:run")
        assert job.enable().disable().enabled is False


class JobExecutionAggregateTest:
    """JobExecutionAggregate 执行记录状态机测试。"""

    def test_start_sets_status_to_running(self) -> None:
        job_id = uuid4()
        execution = JobExecutionAggregate.start(job_id)
        assert execution.status == JobStatus.RUNNING.value
        assert execution.job_id == job_id
        assert execution.finished_at is None
        assert execution.duration_ms is None
        assert execution.error_message is None

    def test_succeed_sets_status_success_and_duration(self) -> None:
        execution = JobExecutionAggregate.start(uuid4())
        done = execution.succeed(1500)
        assert done.status == JobStatus.SUCCESS.value
        assert done.duration_ms == 1500
        assert done.finished_at is not None

    def test_fail_sets_status_failed_and_error_message(self) -> None:
        execution = JobExecutionAggregate.start(uuid4())
        failed = execution.fail("handler raised", 3000)
        assert failed.status == JobStatus.FAILED.value
        assert failed.error_message == "handler raised"
        assert failed.duration_ms == 3000
        assert failed.finished_at is not None

    def test_timeout_sets_status_timeout_and_default_message(self) -> None:
        execution = JobExecutionAggregate.start(uuid4())
        timed = execution.timeout(5000)
        assert timed.status == JobStatus.TIMEOUT.value
        assert timed.duration_ms == 5000
        assert timed.error_message == "Job execution timed out"
        assert timed.finished_at is not None

    def test_start_with_tenant_id(self) -> None:
        tenant_id = uuid4()
        execution = JobExecutionAggregate.start(uuid4(), tenant_id=tenant_id)
        assert execution.tenant_id == tenant_id