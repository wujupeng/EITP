"""INV 定时任务调度器 - 5 个周期任务。

对应 EITP-INV-001-T17-03：
  1. 余额快照校验（每小时）- BalanceSnapshotValidator
  2. 预留过期扫描（每 5 分钟）- 自动释放过期预留
  3. 幂等记录清理（每 10 分钟）- DELETE FROM inv_idempotency_record WHERE expires_at < now()
  4. 负库存申请单超时取消（每 5 分钟）- 扫描 expires_at < now() AND status=pending
  5. 审计归档（每天 02:00）- inv_inventory_audit 保留期 ≥365 天

使用 asyncio 原生任务调度，无外部依赖。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from app.infrastructure.db.session import get_session_factory

logger = logging.getLogger(__name__)

# 保留期常量
_AUDIT_RETENTION_DAYS = 365
_RESERVATION_EXPIRY_BATCH = 500
_IDEMPOTENCY_CLEANUP_BATCH = 1000


class InvScheduler:
    """INV 定时任务调度器。

    在 FastAPI lifespan 中启动 / 停止，使用 asyncio.create_task 管理 5 个周期任务。
    """

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

    async def start(self) -> None:
        """启动所有定时任务。"""
        if self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._balance_snapshot_validator_loop(), name="inv-balance-validator"),
            asyncio.create_task(self._reservation_expiry_loop(), name="inv-reservation-expiry"),
            asyncio.create_task(self._idempotency_cleanup_loop(), name="inv-idempotency-cleanup"),
            asyncio.create_task(self._negative_stock_timeout_loop(), name="inv-negative-stock-timeout"),
            asyncio.create_task(self._audit_archive_loop(), name="inv-audit-archive"),
        ]
        logger.info(
            "InvScheduler started: balance_validator(1h), reservation_expiry(5m), "
            "idempotency_cleanup(10m), negative_stock_timeout(5m), audit_archive(daily)"
        )

    async def stop(self) -> None:
        """停止所有定时任务。"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    # -----------------------------------------------------------------------
    # 1. 余额快照校验 - 每小时
    # -----------------------------------------------------------------------

    async def _balance_snapshot_validator_loop(self) -> None:
        while self._running:
            await asyncio.sleep(3600)
            if not self._running:
                break
            try:
                await self._run_balance_snapshot_validator()
            except Exception:
                logger.exception("balance_snapshot_validator failed")

    async def _run_balance_snapshot_validator(self) -> None:
        """校验 inv_inventory_balance 的 reserved <= on_hand 一致性。"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) AS cnt FROM inv_inventory_balance "
                    "WHERE reserved > on_hand"
                )
            )
            inconsistent_count = result.scalar_one()
            if inconsistent_count > 0:
                logger.warning(
                    "balance_snapshot_inconsistent detected",
                    extra={"inconsistent_count": inconsistent_count},
                )
            else:
                logger.debug("balance_snapshot_validator passed: all balances consistent")

    # -----------------------------------------------------------------------
    # 2. 预留过期扫描 - 每 5 分钟
    # -----------------------------------------------------------------------

    async def _reservation_expiry_loop(self) -> None:
        while self._running:
            await asyncio.sleep(300)
            if not self._running:
                break
            try:
                await self._run_reservation_expiry()
            except Exception:
                logger.exception("reservation_expiry failed")

    async def _run_reservation_expiry(self) -> None:
        """释放过期预留：status=active AND expires_at < now() → status=released。"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE inv_inventory_reservation "
                    "SET status = 'released', updated_at = now() "
                    "WHERE id IN ("
                    "  SELECT id FROM inv_inventory_reservation "
                    "  WHERE status = 'active' AND expires_at < now() "
                    f"  LIMIT {_RESERVATION_EXPIRY_BATCH}"
                    ")"
                )
            )
            released = result.rowcount
            await session.commit()
            if released > 0:
                logger.info("reservation_expired released", extra={"count": released})

    # -----------------------------------------------------------------------
    # 3. 幂等记录清理 - 每 10 分钟
    # -----------------------------------------------------------------------

    async def _idempotency_cleanup_loop(self) -> None:
        while self._running:
            await asyncio.sleep(600)
            if not self._running:
                break
            try:
                await self._run_idempotency_cleanup()
            except Exception:
                logger.exception("idempotency_cleanup failed")

    async def _run_idempotency_cleanup(self) -> None:
        """清理过期幂等记录：DELETE FROM inv_idempotency_record WHERE expires_at < now()。"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    "DELETE FROM inv_idempotency_record "
                    "WHERE id IN ("
                    "  SELECT id FROM inv_idempotency_record "
                    "  WHERE expires_at < now() "
                    f"  LIMIT {_IDEMPOTENCY_CLEANUP_BATCH}"
                    ")"
                )
            )
            deleted = result.rowcount
            await session.commit()
            if deleted > 0:
                logger.info("idempotency_cleanup deleted", extra={"count": deleted})

    # -----------------------------------------------------------------------
    # 4. 负库存申请单超时取消 - 每 5 分钟
    # -----------------------------------------------------------------------

    async def _negative_stock_timeout_loop(self) -> None:
        while self._running:
            await asyncio.sleep(300)
            if not self._running:
                break
            try:
                await self._run_negative_stock_timeout()
            except Exception:
                logger.exception("negative_stock_timeout failed")

    async def _run_negative_stock_timeout(self) -> None:
        """取消超时负库存申请：expires_at < now() AND status=pending → status=cancelled。"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE inv_negative_stock_request "
                    "SET status = 'cancelled', updated_at = now() "
                    "WHERE status = 'pending' AND expires_at < now()"
                )
            )
            cancelled = result.rowcount
            await session.commit()
            if cancelled > 0:
                logger.info("negative_stock_timeout cancelled", extra={"count": cancelled})

    # -----------------------------------------------------------------------
    # 5. 审计归档 - 每天凌晨 02:00
    # -----------------------------------------------------------------------

    async def _audit_archive_loop(self) -> None:
        while self._running:
            now = datetime.now(timezone.utc)
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                from datetime import timedelta
                next_run = next_run + timedelta(days=1)
            wait_seconds = (next_run - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            if not self._running:
                break
            try:
                await self._run_audit_archive()
            except Exception:
                logger.exception("audit_archive failed")

    async def _run_audit_archive(self) -> None:
        """归档超期审计记录（保留期 ≥365 天）。

        V1 实现：仅记录日志标记可归档行数，不实际删除。
        生产环境应迁移到冷存储后删除。
        """
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) AS cnt FROM inv_inventory_audit "
                    f"WHERE created_at < now() - INTERVAL '{_AUDIT_RETENTION_DAYS} days'"
                )
            )
            archivable = result.scalar_one()
            if archivable > 0:
                logger.info(
                    "audit_archive candidates",
                    extra={"archivable_count": archivable, "retention_days": _AUDIT_RETENTION_DAYS},
                )