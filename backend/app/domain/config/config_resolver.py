"""ConfigResolver - 四层配置继承求值。

沿层级路径自下而上查找首个 is_overridden=true 记录，
未找到则取 PlatformDefault。
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from app.domain.config.config_aggregate import TenantConfig


class PlatformDefault:
    """平台默认配置 - 含 value_schema JSON Schema 约束。"""

    def __init__(self, key: str, value: Any, value_schema: dict | None = None) -> None:
        self._key = key
        self._value = value
        self._value_schema = value_schema or {}

    @property
    def key(self) -> str:
        return self._key

    @property
    def value(self) -> Any:
        return self._value

    @property
    def value_schema(self) -> dict:
        return self._value_schema


class ConfigResolver:
    """配置求值器 - 四层继承（Platform → Tenant → Enterprise → Organization）。

    求值规则：沿层级路径自下而上查找首个 is_overridden=true 记录，
    未找到则取 PlatformDefault。
    """

    _cache: dict[str, tuple[Any, float]] = {}
    _CACHE_TTL = 30.0

    @classmethod
    def resolve(
        cls,
        config_key: str,
        hierarchy_configs: list[TenantConfig],
        platform_default: PlatformDefault | None = None,
    ) -> Any:
        """求值配置项。

        Args:
            config_key: 配置键
            hierarchy_configs: 按层级从低到高排列的配置列表
                （Organization → Enterprise → Tenant）
            platform_default: 平台默认配置

        Returns:
            最终生效的配置值
        """
        cache_key = f"{config_key}:{id(hierarchy_configs)}"
        cached = cls._cache_get(cache_key)
        if cached is not None:
            return cached

        for config in hierarchy_configs:
            if config.config_key == config_key and config.is_overridden:
                cls._cache_set(cache_key, config.value)
                return config.value

        if platform_default is not None:
            cls._cache_set(cache_key, platform_default.value)
            return platform_default.value

        return None

    @classmethod
    def invalidate_cache(cls, config_key: str | None = None) -> None:
        """失效缓存。"""
        if config_key is None:
            cls._cache.clear()
        else:
            keys_to_remove = [k for k in cls._cache if k.startswith(f"{config_key}:")]
            for k in keys_to_remove:
                cls._cache.pop(k, None)

    @classmethod
    def _cache_get(cls, key: str) -> Any | None:
        entry = cls._cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            cls._cache.pop(key, None)
            return None
        return value

    @classmethod
    def _cache_set(cls, key: str, value: Any) -> None:
        cls._cache[key] = (value, time.monotonic() + cls._CACHE_TTL)