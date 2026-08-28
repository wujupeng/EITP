"""T05 租户配置与功能开关单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.config.config_aggregate import ConfigAggregate, TenantConfig
from app.domain.config.config_resolver import ConfigResolver, PlatformDefault
from app.domain.config.feature_flag import FeatureFlag
from app.domain.shared.entity import EntityId


class TestFeatureFlag:
    def test_feature_flag_on(self) -> None:
        flag = FeatureFlag(tenant_id=uuid4(), feature_key="sales", enabled=True)
        assert flag.is_on() is True

    def test_feature_flag_off(self) -> None:
        flag = FeatureFlag(tenant_id=uuid4(), feature_key="sales", enabled=False)
        assert flag.is_on() is False

    def test_toggle(self) -> None:
        flag = FeatureFlag(tenant_id=uuid4(), feature_key="sales", enabled=True)
        toggled = flag.toggle(False)
        assert toggled.is_on() is False
        assert flag.is_on() is True


class TestConfigAggregate:
    def test_set_feature_flag(self) -> None:
        tenant_id = uuid4()
        agg = ConfigAggregate(EntityId.generate(), tenant_id)
        flag = FeatureFlag(tenant_id=tenant_id, feature_key="sales", enabled=True)
        agg.set_feature_flag(flag)
        assert agg.is_feature_on("sales") is True

    def test_toggle_feature_flag_records_event(self) -> None:
        tenant_id = uuid4()
        agg = ConfigAggregate(EntityId.generate(), tenant_id)
        agg.set_feature_flag(FeatureFlag(tenant_id=tenant_id, feature_key="sales", enabled=True))
        agg.set_feature_flag(FeatureFlag(tenant_id=tenant_id, feature_key="sales", enabled=False))
        events = list(agg.pull_events())
        assert len(events) == 1
        assert events[0].event_type == "FeatureFlagChangedEvent"
        assert events[0].new_enabled is False

    def test_set_config_records_event(self) -> None:
        tenant_id = uuid4()
        agg = ConfigAggregate(EntityId.generate(), tenant_id)
        agg.set_config(key="tax_rate", value=0.13, changed_by=uuid4())
        events = list(agg.pull_events())
        assert len(events) == 1
        assert events[0].event_type == "ConfigChangedEvent"
        assert events[0].new_value == 0.13

    def test_set_config_no_event_on_same_value(self) -> None:
        tenant_id = uuid4()
        agg = ConfigAggregate(EntityId.generate(), tenant_id)
        agg.set_config(key="tax_rate", value=0.13)
        agg.set_config(key="tax_rate", value=0.13)
        events = list(agg.pull_events())
        assert len(events) == 1

    def test_is_feature_on_default_true(self) -> None:
        agg = ConfigAggregate(EntityId.generate(), uuid4())
        assert agg.is_feature_on("unknown") is True


class TestConfigResolver:
    def setup_method(self) -> None:
        ConfigResolver.invalidate_cache()

    def test_resolve_explicit_override(self) -> None:
        tenant_id = uuid4()
        configs = [
            TenantConfig(tenant_id=tenant_id, config_key="tax_rate", value=0.10, is_overridden=True),
        ]
        result = ConfigResolver.resolve("tax_rate", configs)
        assert result == 0.10

    def test_resolve_platform_default(self) -> None:
        configs: list[TenantConfig] = []
        default = PlatformDefault(key="tax_rate", value=0.13)
        result = ConfigResolver.resolve("tax_rate", configs, default)
        assert result == 0.13

    def test_resolve_override_takes_priority_over_default(self) -> None:
        tenant_id = uuid4()
        configs = [
            TenantConfig(tenant_id=tenant_id, config_key="tax_rate", value=0.10, is_overridden=True),
        ]
        default = PlatformDefault(key="tax_rate", value=0.13)
        result = ConfigResolver.resolve("tax_rate", configs, default)
        assert result == 0.10

    def test_resolve_skip_non_overridden(self) -> None:
        tenant_id = uuid4()
        configs = [
            TenantConfig(tenant_id=tenant_id, config_key="tax_rate", value=0.10, is_overridden=False),
        ]
        default = PlatformDefault(key="tax_rate", value=0.13)
        result = ConfigResolver.resolve("tax_rate", configs, default)
        assert result == 0.13

    def test_resolve_four_level_inheritance(self) -> None:
        tenant_id = uuid4()
        configs = [
            TenantConfig(tenant_id=tenant_id, config_key="tax_rate", value=0.08, is_overridden=False, scope_level="organization"),
            TenantConfig(tenant_id=tenant_id, config_key="tax_rate", value=0.10, is_overridden=True, scope_level="enterprise"),
            TenantConfig(tenant_id=tenant_id, config_key="tax_rate", value=0.12, is_overridden=False, scope_level="tenant"),
        ]
        default = PlatformDefault(key="tax_rate", value=0.13)
        result = ConfigResolver.resolve("tax_rate", configs, default)
        assert result == 0.10

    def test_resolve_cache_hit(self) -> None:
        tenant_id = uuid4()
        configs = [
            TenantConfig(tenant_id=tenant_id, config_key="tax_rate", value=0.10, is_overridden=True),
        ]
        result1 = ConfigResolver.resolve("tax_rate", configs)
        result2 = ConfigResolver.resolve("tax_rate", configs)
        assert result1 == result2 == 0.10

    def test_invalidate_cache(self) -> None:
        tenant_id = uuid4()
        configs = [
            TenantConfig(tenant_id=tenant_id, config_key="tax_rate", value=0.10, is_overridden=True),
        ]
        ConfigResolver.resolve("tax_rate", configs)
        ConfigResolver.invalidate_cache("tax_rate")
        assert len(ConfigResolver._cache) == 0 or not any(k.startswith("tax_rate:") for k in ConfigResolver._cache)

    def test_resolve_none_when_no_config(self) -> None:
        result = ConfigResolver.resolve("unknown_key", [])
        assert result is None


class TestTenantConfig:
    def test_override_sets_is_overridden(self) -> None:
        config = TenantConfig(tenant_id=uuid4(), config_key="tax_rate", value=0.13, is_overridden=False)
        overridden = config.override(0.10)
        assert overridden.is_overridden is True
        assert overridden.value == 0.10

    def test_default_scope_level(self) -> None:
        config = TenantConfig(tenant_id=uuid4(), config_key="tax_rate", value=0.13)
        assert config.scope_level == "tenant"