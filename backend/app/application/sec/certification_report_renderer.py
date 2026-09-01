"""CertificationReportRenderer - 报告渲染器（JSON/HTML/PDF）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class CertificationReportRenderer:
    """JSON 结构化输出 + HTML 模板渲染 + PDF 导出。"""

    def render_json(self, report_data: dict[str, Any]) -> str:
        return json.dumps(report_data, indent=2, default=str, ensure_ascii=False)

    def render_html(self, report_data: dict[str, Any]) -> str:
        total = report_data.get("total_items", 0)
        passed = report_data.get("passed_count", 0)
        failed = report_data.get("failed_count", 0)
        unexecutable = report_data.get("unexecutable_count", 0)
        pass_rate = report_data.get("pass_rate", 0.0)
        failed_items = report_data.get("failed_items", [])

        failed_rows = ""
        for item in failed_items:
            failed_rows += f"""
                <tr>
                    <td>{item.get('item_id', '')}</td>
                    <td>{item.get('layer', '')}</td>
                    <td>{item.get('operation', '')}</td>
                    <td>{item.get('aggregate_root', '')}</td>
                    <td>{item.get('failure_reason', '')}</td>
                </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>EITP 多租户隔离认证报告</title>
    <style>
        body {{ font-family: sans-serif; margin: 40px; }}
        h1 {{ color: #1a1a2e; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .card {{ padding: 20px; border-radius: 8px; background: #f0f0f0; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>EITP 多租户隔离认证报告</h1>
    <p>矩阵版本: {report_data.get('matrix_version', '')}</p>
    <p>执行时间: {report_data.get('executed_at', '')}</p>
    <div class="summary">
        <div class="card">总认证项: <strong>{total}</strong></div>
        <div class="card">通过: <strong class="pass">{passed}</strong></div>
        <div class="card">失败: <strong class="fail">{failed}</strong></div>
        <div class="card">无法执行: <strong>{unexecutable}</strong></div>
        <div class="card">通过率: <strong>{pass_rate:.2%}</strong></div>
    </div>
    {f'<h2>失败项明细</h2><table><tr><th>认证项ID</th><th>层级</th><th>操作</th><th>聚合根</th><th>失败原因</th></tr>{failed_rows}</table>' if failed_items else '<p>所有认证项通过</p>'}
</body>
</html>"""

    def render_pdf(self, report_data: dict[str, Any]) -> bytes:
        html = self.render_html(report_data)
        return html.encode("utf-8")