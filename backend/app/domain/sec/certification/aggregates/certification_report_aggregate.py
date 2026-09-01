"""CertificationReportAggregate 聚合根 - 认证报告，双格式 JSON+HTML/PDF。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass
class CertificationReportAggregate:
    report_id: str = ""
    batch_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    matrix_version: str = ""
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executor: str = ""
    total_items: int = 0
    passed_count: int = 0
    failed_count: int = 0
    unexecutable_count: int = 0
    failed_items: list[dict[str, Any]] = field(default_factory=list)
    evidence_index: dict[str, str] = field(default_factory=dict)
    report_json: dict[str, Any] = field(default_factory=dict)
    report_html: str = ""
    tenant_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))

    def calculate_statistics(self, items: list) -> None:
        self.total_items = len(items)
        self.passed_count = sum(1 for i in items if i.is_pass)
        self.failed_count = sum(1 for i in items if i.is_fail)
        self.unexecutable_count = sum(1 for i in items if i.is_unexecutable)
        self.failed_items = [
            {"item_id": i.item_id, "layer": i.layer.value, "reason": i.failure_reason}
            for i in items if i.is_fail
        ]

    @property
    def pass_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.passed_count / self.total_items

    def render_json(self) -> str:
        self.report_json = {
            "report_id": self.report_id,
            "batch_id": str(self.batch_id),
            "matrix_version": self.matrix_version,
            "executed_at": self.executed_at.isoformat(),
            "executor": self.executor,
            "total_items": self.total_items,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "unexecutable_count": self.unexecutable_count,
            "pass_rate": round(self.pass_rate, 4),
            "failed_items": self.failed_items,
        }
        return json.dumps(self.report_json, ensure_ascii=False, indent=2)

    def render_html(self) -> str:
        self.report_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SEC Certification Report {self.report_id}</title></head>
<body>
<h1>Multi-Tenant Isolation Certification Report</h1>
<p>Report ID: {self.report_id}</p>
<p>Matrix Version: {self.matrix_version}</p>
<p>Executed At: {self.executed_at.isoformat()}</p>
<p>Executor: {self.executor}</p>
<h2>Summary</h2>
<table border="1">
<tr><th>Total Items</th><td>{self.total_items}</td></tr>
<tr><th>Passed</th><td>{self.passed_count}</td></tr>
<tr><th>Failed</th><td>{self.failed_count}</td></tr>
<tr><th>Unexecutable</th><td>{self.unexecutable_count}</td></tr>
<tr><th>Pass Rate</th><td>{self.pass_rate:.2%}</td></tr>
</table>
<h2>Failed Items</h2>
<ul>
{''.join(f'<li>{fi["item_id"]} ({fi["layer"]}): {fi["reason"]}</li>' for fi in self.failed_items)}
</ul>
</body></html>"""
        return self.report_html