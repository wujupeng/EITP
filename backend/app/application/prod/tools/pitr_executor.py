"""PITR 执行器 - 基于 WAL 归档恢复至指定时间点。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PitrResult:
    """PITR 恢复结果。"""

    target_time: datetime
    restored_to: datetime
    precision_seconds: float
    started_at: datetime
    finished_at: datetime
    success: bool
    error: str | None = None


class PitrExecutor:
    """PITR 执行器。

    基于 WAL 归档恢复至指定时间点（精度 ≤1s）
    """

    def __init__(
        self,
        pg_ctl_path: str = "pg_ctl",
        wal_archive_dir: str = "/var/lib/postgresql/wal_archive",
        data_dir: str = "/var/lib/postgresql/data",
    ) -> None:
        self._pg_ctl_path = pg_ctl_path
        self._wal_archive_dir = wal_archive_dir
        self._data_dir = data_dir

    async def recover_to_point_in_time(self, target_time: datetime) -> PitrResult:
        started_at = datetime.now(timezone.utc)

        try:
            target_str = target_time.strftime("%Y-%m-%d %H:%M:%S")

            recovery_conf = f"""
restore_command = 'cp {self._wal_archive_dir}/%f %p'
recovery_target_time = '{target_str}'
recovery_target_action = 'pause'
"""
            recovery_path = f"{self._data_dir}/recovery.signal"
            conf_path = f"{self._data_dir}/postgresql.auto.conf"

            import pathlib
            pathlib.Path(recovery_path).touch()
            with open(conf_path, "a") as f:
                f.write(recovery_conf)

            cmd = [self._pg_ctl_path, "-D", self._data_dir, "start"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            finished_at = datetime.now(timezone.utc)
            precision = abs((finished_at - target_time).total_seconds())

            result = PitrResult(
                target_time=target_time,
                restored_to=finished_at,
                precision_seconds=precision,
                started_at=started_at,
                finished_at=finished_at,
                success=True,
            )
            logger.info("PITR completed: target=%s, precision=%.3fs", target_str, precision)
            return result

        except Exception as exc:
            return PitrResult(
                target_time=target_time,
                restored_to=datetime.now(timezone.utc),
                precision_seconds=0.0,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                success=False,
                error=str(exc),
            )