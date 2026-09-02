"""pgbench 数据库压测适配器。"""

from __future__ import annotations

import asyncio
from typing import Any

from app.application.prod.tools.load_test_engine_adapter import LoadTestEngineAdapter


class PgbenchAdapter(LoadTestEngineAdapter):
    """封装 pgbench 数据库压测。"""

    def __init__(self, pgbench_path: str = "pgbench") -> None:
        self._pgbench_path = pgbench_path

    @property
    def engine_name(self) -> str:
        return "pgbench"

    async def _run_engine(self, target_url: str, duration_seconds: int, concurrency: int, **kwargs: Any) -> dict[str, Any]:
        dsn = kwargs.get("dsn", target_url)
        scale = kwargs.get("scale", 10)
        cmd = [
            self._pgbench_path,
            "-c", str(concurrency),
            "-j", str(concurrency),
            "-T", str(duration_seconds),
            "-s", str(scale),
            dsn,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace")

        tps = 0.0
        import re
        tps_match = re.search(r"tps =\s+([\d.]+)", output)
        if tps_match:
            tps = float(tps_match.group(1))

        return {
            "total_requests": int(tps * duration_seconds) if tps > 0 else 0,
            "success_count": int(tps * duration_seconds) if tps > 0 else 0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "qps": tps,
            "raw_output": output[:4096],
        }