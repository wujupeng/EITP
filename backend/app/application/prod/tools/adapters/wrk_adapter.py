"""wrk 压测引擎适配器 - 单端点高 QPS。"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from app.application.prod.tools.load_test_engine_adapter import LoadTestEngineAdapter


class WrkAdapter(LoadTestEngineAdapter):
    """封装 wrk 单端点高 QPS 压测，精确测量 P50/P95/P99。"""

    def __init__(self, wrk_path: str = "wrk") -> None:
        self._wrk_path = wrk_path

    @property
    def engine_name(self) -> str:
        return "wrk"

    async def _run_engine(self, target_url: str, duration_seconds: int, concurrency: int, **kwargs: Any) -> dict[str, Any]:
        threads = kwargs.get("threads", concurrency)
        cmd = [
            self._wrk_path, "-t", str(threads),
            "-c", str(concurrency),
            "-d", f"{duration_seconds}s",
            "--latency",
            target_url,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace")

        qps = 0.0
        p50 = p95 = p99 = 0.0
        total = success = 0

        qps_match = re.search(r"Requests/sec:\s+([\d.]+)", output)
        if qps_match:
            qps = float(qps_match.group(1))

        lat_match = re.search(r"Latency\s+([\d.]+)(\w+)", output)
        if lat_match:
            p50 = float(lat_match.group(1))

        p95_match = re.search(r"95%\s+([\d.]+)", output)
        if p95_match:
            p95 = float(p95_match.group(1))

        p99_match = re.search(r"99%\s+([\d.]+)", output)
        if p99_match:
            p99 = float(p99_match.group(1))

        req_match = re.search(r"(\d+) requests in", output)
        if req_match:
            total = int(req_match.group(1))
            success = total

        return {
            "total_requests": total,
            "success_count": success,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "qps": qps,
            "raw_output": output[:4096],
        }