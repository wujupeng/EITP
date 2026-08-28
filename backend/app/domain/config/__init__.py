"""Config Bounded Context - 租户配置与功能开关。"""

from app.domain.config.config_aggregate import ConfigAggregate, TenantConfig
from app.domain.config.config_events import ConfigChangedEvent, FeatureFlagChangedEvent
from app.domain.config.config_resolver import ConfigResolver, PlatformDefault
from app.domain.config.feature_flag import FeatureFlag

__all__ = [
    "ConfigAggregate",
    "ConfigChangedEvent",
    "ConfigResolver",
    "FeatureFlag",
    "FeatureFlagChangedEvent",
    "PlatformDefault",
    "TenantConfig",
]
