"""WMS 定时任务调度器 - 3 个周期任务。

对应 EITP-WMS-001-T18-03：
  1. WMS↔INV 对账（每小时）- 对比 Inventory Position 聚合与 INV Balance，记录差异
  2. Task 超时巡检（每 10 分钟）- 扫描 IN_PROGRESS 超时 Task，告警
  3. 效期预警（P1，每日）- 扫描即将过期商品

使用 asyncio 原生任务调度，复用 INV/MDM scheduler 模式。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory

logger = logging.getLogger(__name__)

_RECONCILE_INTERVAL_SECONDS = 3600
_TASK_TIMEOUT_CHECK_INTERVAL_SECONDS = 600
_TASK_TIMEOUT_SECONDS = 7200
_EXPIRY_WARNING_INTERVAL_SECONDS = 86400
_EXPIRY_WARNING_DAYS = 30


class WmsScheduler:
    """WMS 定时任务调度器。

    在 FastAPI lifespan 中启动 / 停止，使用 asyncio.create_task 管理 3 个周期任务。
    """

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._reconcile_loop(), name="wms-reconcile"),
            asyncio.create_task(self._task_timeout_loop(), name="wms-task-timeout"),
            asyncio.create_task(self._expiry_warning_loop(), name="wms-expiry-warning"),
        ]
        logger.info(
            "WmsScheduler started: reconcile(1h), task_timeout(10m), expiry_warning(daily)"
        )

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks = []
        logger.info("WmsScheduler stopped")

    async def _reconcile_loop(self) -> None:
        while self._running:
            try:
                await self._run_reconcile()
            except Exception:
                logger.exception("WMS reconcile job failed")
            await asyncio.sleep(_RECONCILE_INTERVAL_SECONDS)

    async def _task_timeout_loop(self) -> None:
        while self._running:
            try:
                await self._check_task_timeout()
            except Exception:
                logger.exception("WMS task timeout check failed")
            await asyncio.sleep(_TASK_TIMEOUT_CHECK_INTERVAL_SECONDS)

    async def _expiry_warning_loop(self) -> None:
        while self._running:
            try:
                await self._check_expiry_warning()
            except Exception:
                logger.exception("WMS expiry warning job failed")
            await asyncio.sleep(_EXPIRY_WARNING_INTERVAL_SECONDS)

    async def _run_reconcile(self) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(text("""
                SELECT w.tenant_id, w.warehouse_id, w.sku_id,
                       SUM(w.quantity) AS wms_qty,
                       COALESCE(i.on_hand, 0) AS inv_qty
                FROM wms_inventory_position w
                LEFT JOIN inv_inventory_balance i
                  ON i.tenant_id = w.tenant_id
                 AND i.sku_id = w.sku_id
                 AND i.warehouse_id = w.warehouse_id
                WHERE w.inventory_status = 'available'
                GROUP BY w.tenant_id, w.warehouse_id, w.sku_id, i.on_hand
                HAVING SUM(w.quantity) != COALESCE(i.on_hand, 0)
            """))
            diffs = result.fetchall()
            if diffs:
                logger.warning("WMS↔INV reconcile found %d differences", len(diffs))
                for diff in diffs:
                    await session.execute(text("""
                        INSERT INTO wms_reconcile_diff
                            (tenant_id, sku_id, warehouse_id, wms_quantity, inv_quantity,
                             diff_quantity, diff_type, status, created_at)
                        VALUES
                            (:tenant_id, :sku_id, :warehouse_id, :wms_qty, :inv_qty,
                             :diff_qty, :diff_type, 'open', now())
                    """), {
                        "tenant_id": diff.tenant_id,
                        "sku_id": diff.sku_id,
                        "warehouse_id": diff.warehouse_id,
                        "wms_qty": float(diff.wms_qty),
                        "inv_qty": float(diff.inv_qty),
                        "diff_qty": float(diff.wms_qty) - float(diff.inv_qty),
                        "diff_type": "wms_more" if diff.wms_qty > diff.inv_qty else "inv_more",
                    })
                await session.commit()
            else:
                logger.info("WMS↔INV reconcile: no differences found")

    async def _check_task_timeout(self) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(text("""
                SELECT task_id, tenant_id, task_type, started_at
                FROM wms_task
                WHERE status = 'in_progress'
                  AND started_at < now() - interval '%s seconds'
            """ % _TASK_TIMEOUT_SECONDS))
            timed_out = result.fetchall()
            if timed_out:
                logger.warning("Found %d timed-out WMS tasks", len(timed_out))
                for task in timed_out:
                    logger.warning(
                        "WMS Task %s (type=%s) timed out, started_at=%s",
                        task.task_id, task.task_type, task.started_at,
                    )

    async def _check_expiry_warning(self) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(text("""
                SELECT position_id, tenant_id, sku_id, expiry_date, quantity
                FROM wms_inventory_position
                WHERE expiry_date IS NOT NULL
                  AND expiry_date <= now() + interval '%s days'
                  AND quantity > 0
            """ % _EXPIRY_WARNING_DAYS))
            expiring = result.fetchall()
            if expiring:
                logger.info("Found %d items nearing expiry", len(expiring))
            else:
                logger.debug("No items nearing expiry")