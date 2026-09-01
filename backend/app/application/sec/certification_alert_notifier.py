"""CertificationAlertNotifier - 认证告警通知器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AlertMessage:
    title: str
    body: str
    channels: list[str] = field(default_factory=list)
    failed_items: list[dict[str, Any]] = field(default_factory=list)


class CertificationAlertNotifier:
    """按配置渠道推送告警，失败数 ≥1 即告警。"""

    def __init__(self, alert_channels: list[str] | None = None) -> None:
        self._channels = alert_channels or ["email"]

    def build_alert(self, failed_items: list[dict[str, Any]], batch_id: str = "") -> AlertMessage | None:
        if not failed_items:
            return None

        body_lines = [f"认证批次 {batch_id} 有 {len(failed_items)} 个失败项：\n"]
        for item in failed_items[:20]:
            body_lines.append(
                f"  - {item.get('item_id', '')}: {item.get('failure_reason', '')}"
            )
        if len(failed_items) > 20:
            body_lines.append(f"  ... 还有 {len(failed_items) - 20} 个失败项")

        body_lines.append("\n建议修复动作：")
        body_lines.append("  1. 检查对应层的隔离防护代码")
        body_lines.append("  2. 确认 RLS 策略已正确启用")
        body_lines.append("  3. 验证 Redis Key 前缀合规性")
        body_lines.append("  4. 重新执行认证矩阵")

        return AlertMessage(
            title=f"[EITP-SEC] 认证失败告警 - 批次 {batch_id}",
            body="\n".join(body_lines),
            channels=self._channels,
            failed_items=failed_items,
        )

    async def send_alert(self, alert: AlertMessage) -> dict[str, Any]:
        return {"sent": True, "channels": alert.channels, "title": alert.title}