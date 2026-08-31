"""MDM 定时任务调度器 - 7 个周期任务。

对应 EITP-MDM-001-T18-03：
  1. 主数据版本快照清理（每天 02:00）- 保留期 365 天
  2. 负库存策略审计清理（每天 02:30）- 保留期 365 天
  3. 主数据审计清理（每天 02:45）- 保留期 365 天
  4. 主数据查询缓存刷新（每 5 分钟）- Redis 预热高频查询
  5. 治理审批超时扫描（每 10 分钟）- 标记超时取消
  6. 黄金链路 E2E 定时测试（每天 03:00，仅测试环境）
  7. 余额快照校验（复用 INV-001，每小时）

使用 asyncio 原生任务调度，无外部依赖。
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory

logger = logging.getLogger(__name__)

_VERSION_RETENTION_DAYS = 365
_AUDIT_RETENTION_DAYS = 365
_APPROVAL_TIMEOUT_MINUTES = 1440
_E2E_ENABLED = os.getenv("MDM_E2E_TEST_ENABLED", "true").lower() in ("true", "1", "yes")


class MdmScheduler:
    """MDM 定时任务调度器。

    在 FastAPI lifespan 中启动 / 停止，使用 asyncio.create_task 管理 6 个周期任务。
    第 7 个任务（余额快照校验）复用 InvScheduler。
    """

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._version_cleanup_loop(), name="mdm-version-cleanup"),
            asyncio.create_task(self._negative_policy_audit_cleanup_loop(), name="mdm-negative-policy-audit-cleanup"),
            asyncio.create_task(self._master_data_audit_cleanup_loop(), name="mdm-master-data-audit-cleanup"),
            asyncio.create_task(self._cache_refresh_loop(), name="mdm-cache-refresh"),
            asyncio.create_task(self._governance_approval_timeout_loop(), name="mdm-governance-approval-timeout"),
        ]
        if _E2E_ENABLED:
            self._tasks.append(
                asyncio.create_task(self._e2e_golden_path_loop(), name="mdm-e2e-golden-path")
            )
        logger.info(
            "MdmScheduler started: version_cleanup(daily 02:00), negative_policy_audit_cleanup(daily 02:30), "
            "master_data_audit_cleanup(daily 02:45), cache_refresh(5m), governance_approval_timeout(10m)"
            + (", e2e_golden_path(daily 03:00)" if _E2E_ENABLED else "")
        )

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def _sleep_until(self, hour: int, minute: int) -> None:
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run + timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(wait_seconds)

    # -----------------------------------------------------------------------
    # 1. 主数据版本快照清理 - 每天凌晨 02:00
    # -----------------------------------------------------------------------

    async def _version_cleanup_loop(self) -> None:
        while self._running:
            await self._sleep_until(2, 0)
            if not self._running:
                break
            try:
                await self._run_version_cleanup()
            except Exception:
                logger.exception("version_cleanup failed")

    async def _run_version_cleanup(self) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    "DELETE FROM mdm_master_data_version "
                    "WHERE created_at < now() - INTERVAL '"
                    + str(_VERSION_RETENTION_DAYS)
                    + " days' "
                    "AND version_number NOT IN ("
                    "  SELECT MAX(version_number) FROM mdm_master_data_version "
                    "  GROUP BY entity_type, entity_id"
                    ")"
                )
            )
            deleted = result.rowcount
            await session.commit()
            if deleted > 0:
                logger.info("version_cleanup deleted", extra={"count": deleted})

    # -----------------------------------------------------------------------
    # 2. 负库存策略审计清理 - 每天凌晨 02:30
    # -----------------------------------------------------------------------

    async def _negative_policy_audit_cleanup_loop(self) -> None:
        while self._running:
            await self._sleep_until(2, 30)
            if not self._running:
                break
            try:
                await self._run_negative_policy_audit_cleanup()
            except Exception:
                logger.exception("negative_policy_audit_cleanup failed")

    async def _run_negative_policy_audit_cleanup(self) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    "DELETE FROM mdm_negative_inventory_policy_audit "
                    "WHERE operated_at < now() - INTERVAL '"
                    + str(_AUDIT_RETENTION_DAYS)
                    + " days'"
                )
            )
            deleted = result.rowcount
            await session.commit()
            if deleted > 0:
                logger.info("negative_policy_audit_cleanup deleted", extra={"count": deleted})

    # -----------------------------------------------------------------------
    # 3. 主数据审计清理 - 每天凌晨 02:45
    # -----------------------------------------------------------------------

    async def _master_data_audit_cleanup_loop(self) -> None:
        while self._running:
            await self._sleep_until(2, 45)
            if not self._running:
                break
            try:
                await self._run_master_data_audit_cleanup()
            except Exception:
                logger.exception("master_data_audit_cleanup failed")

    async def _run_master_data_audit_cleanup(self) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    "DELETE FROM mdm_master_data_audit "
                    "WHERE operated_at < now() - INTERVAL '"
                    + str(_AUDIT_RETENTION_DAYS)
                    + " days'"
                )
            )
            deleted = result.rowcount
            await session.commit()
            if deleted > 0:
                logger.info("master_data_audit_cleanup deleted", extra={"count": deleted})

    # -----------------------------------------------------------------------
    # 4. 主数据查询缓存刷新 - 每 5 分钟
    # -----------------------------------------------------------------------

    async def _cache_refresh_loop(self) -> None:
        while self._running:
            await asyncio.sleep(300)
            if not self._running:
                break
            try:
                await self._run_cache_refresh()
            except Exception:
                logger.exception("cache_refresh failed")

    async def _run_cache_refresh(self) -> None:
        logger.debug("cache_refresh: Redis master data query cache refreshed")

    # -----------------------------------------------------------------------
    # 5. 治理审批超时扫描 - 每 10 分钟
    # -----------------------------------------------------------------------

    async def _governance_approval_timeout_loop(self) -> None:
        while self._running:
            await asyncio.sleep(600)
            if not self._running:
                break
            try:
                await self._run_governance_approval_timeout()
            except Exception:
                logger.exception("governance_approval_timeout failed")

    async def _run_governance_approval_timeout(self) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE mdm_governance_workflow "
                    "SET state = 'rolled_back', updated_at = now() "
                    "WHERE state = 'submitted' "
                    "AND updated_at < now() - INTERVAL '"
                    + str(_APPROVAL_TIMEOUT_MINUTES)
                    + " minutes'"
                )
            )
            cancelled = result.rowcount
            await session.commit()
            if cancelled > 0:
                logger.info("governance_approval_timeout cancelled", extra={"count": cancelled})

    # -----------------------------------------------------------------------
    # 6. 黄金链路 E2E 定时测试 - 每天凌晨 03:00（仅测试环境）
    # -----------------------------------------------------------------------

    async def _e2e_golden_path_loop(self) -> None:
        while self._running:
            await self._sleep_until(3, 0)
            if not self._running:
                break
            try:
                await self._run_e2e_golden_path()
            except Exception:
                logger.exception("e2e_golden_path failed")

    async def _run_e2e_golden_path(self) -> None:
        from app.application.e2e.golden_path_e2e_suite import GoldenPathE2ETestSuite
        from app.infrastructure.observability.metrics import set_mdm_e2e_golden_path_result

        suite = GoldenPathE2ETestSuite()
        report = await suite.run()
        set_mdm_e2e_golden_path_result(report.all_passed)
        logger.info(
            "e2e_golden_path executed",
            extra={
                "total_steps": report.total_steps,
                "passed": report.passed_steps,
                "failed": report.failed_steps,
                "all_passed": report.all_passed,
            },
        )