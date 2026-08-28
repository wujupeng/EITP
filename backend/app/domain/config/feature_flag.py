"""功能开关值对象 - 租户级独立、即时生效。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class FeatureFlag:
    """功能开关 - 按 (tenant_id, feature_key) 复合主键隔离。

    支持即时生效：开关切换时立即失效缓存。
    """

    tenant_id: UUID
    feature_key: str
    enabled: bool = True

    def toggle(self, enabled: bool) -> FeatureFlag:
        """切换开关状态。"""
        return FeatureFlag(
            tenant_id=self.tenant_id,
            feature_key=self.feature_key,
            enabled=enabled,
        )

    def is_on(self) -> bool:
        return self.enabled