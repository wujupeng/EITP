"""Locust 压测引擎适配器 - 多租户并发场景。"""

from __future__ import annotations

import asyncio
from typing import Any

from app.application.prod.tools.load_test_engine_adapter import LoadTestEngineAdapter


class LocustAdapter(LoadTestEngineAdapter):
    """封装 Locust 多租户并发场景脚本执行，支持阶梯递增并发。"""

    def __init__(self, locust_path: str = "locust") -> None:
        self._locust_path = locust_path

    @property
    def engine_name(self) -> str:
        return "locust"

    async def _run_engine(self, target_url: str, duration_seconds: int, concurrency: int, **kwargs: Any) -> dict[str, Any]:
        locustfile = kwargs.get("locustfile", "locustfile.py")
        spawn_rate = kwargs.get("spawn_rate", concurrency // 10 or 1)
        cmd = [
            self._locust_path, "-f", locustfile,
            "--headless", "--host", target_url,
            "-u", str(concurrency), "-r", str(spawn_rate),
            "--run-time", f"{duration_seconds}s",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "total_requests": 0,
            "success_count": 0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "qps": 0.0,
            "stdout": stdout.decode("utf-8", errors="replace")[:4096],
            "stderr": stderr.decode("utf-8", errors="replace")[:4096],
            "exit_code": proc.returncode,
        }