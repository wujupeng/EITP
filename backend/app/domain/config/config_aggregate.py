"""配置聚合根与 TenantConfig 值对象 - 含 is_overridden 显式覆盖标记。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.config.config_events import ConfigChangedEvent, FeatureFlagChangedEvent
from app.domain.config.feature_flag import FeatureFlag
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId


@dataclass(frozen=True)
class TenantConfig:
    """租户配置值对象 - 含 is_overridden 显式覆盖标记。

    is_overridden=true 表示本层级显式覆盖了上层继承值。
    is_overridden=false 表示使用继承值（不参与求值）。
    """

    tenant_id: UUID
    config_key: str
    value: Any
    is_overridden: bool = False
    scope_level: str = "tenant"

    def override(self, new_value: Any) -> TenantConfig:
        """显式覆盖配置值。"""
        return TenantConfig(
            tenant_id=self.tenant_id,
            config_key=self.config_key,
            value=new_value,
            is_overridden=True,
            scope_level=self.scope_level,
        )


class ConfigAggregate(AggregateRoot):
    """配置聚合根 - 管理功能开关与配置项的一致性。"""

    def __init__(self, id: EntityId, tenant_id: UUID) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._feature_flags: dict[str, FeatureFlag] = {}
        self._configs: dict[str, TenantConfig] = {}

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    def set_feature_flag(self, flag: FeatureFlag) -> None:
        """设置功能开关。"""
        old = self._feature_flags.get(flag.feature_key)
        self._feature_flags[flag.feature_key] = flag
        if old is not None and old.enabled != flag.enabled:
            self._record_event(
                FeatureFlagChangedEvent(
                    tenant_id=self._tenant_id,
                    feature_key=flag.feature_key,
                    old_enabled=old.enabled,
                    new_enabled=flag.enabled,
                )
            )

    def get_feature_flag(self, key: str) -> FeatureFlag | None:
        return self._feature_flags.get(key)

    def is_feature_on(self, key: str) -> bool:
        flag = self._feature_flags.get(key)
        return flag.is_on() if flag else True

    def set_config(
        self,
        key: str,
        value: Any,
        is_overridden: bool = True,
        scope_level: str = "tenant",
        changed_by: UUID | None = None,
    ) -> None:
        """设置配置项。"""
        old = self._configs.get(key)
        new_config = TenantConfig(
            tenant_id=self._tenant_id,
            config_key=key,
            value=value,
            is_overridden=is_overridden,
            scope_level=scope_level,
        )
        self._configs[key] = new_config
        if old is None or old.value != value:
            self._record_event(
                ConfigChangedEvent(
                    tenant_id=self._tenant_id,
                    config_key=key,
                    old_value=old.value if old else None,
                    new_value=value,
                    changed_by=changed_by,
                )
            )

    def get_config(self, key: str) -> TenantConfig | None:
        return self._configs.get(key)