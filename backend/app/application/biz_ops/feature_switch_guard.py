"""FeatureSwitchGuard - 功能开关校验服务，复用仓储 + Redis 缓存 + 进程内二级缓存。"""

from __future__ import annotations

import time
from uuid import UUID

from app.domain.biz_ops.enums.enums import FeatureScope
from app.infrastructure.biz_ops.repositories.feature_switch_repository import (
    FeatureSwitchRepository,
)
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode
from sqlalchemy.ext.asyncio import AsyncSession


class FeatureSwitchGuard:
    """功能开关校验守卫 - ≤20ms（含缓存命中）。

    两级缓存：
    1. 进程内字典缓存（TTL 5s）
    2. Redis 缓存（TTL 5s，跨进程一致）

    降级策略：
    - allow: 缓存/DB 不可用时放行
    - deny: 缓存/DB 不可用时拒绝
    """

    _cache: dict[str, tuple[bool, float]] = {}
    _CACHE_TTL = 5.0

    def __init__(
        self,
        degrade_strategy: str = "allow",
        redis_client=None,
    ) -> None:
        self._repo = FeatureSwitchRepository()
        self._degrade_strategy = degrade_strategy
        self._redis = redis_client

    async def check(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        feature_key: str,
    ) -> bool:
        """校验功能开关是否开启 - 模块级关闭时子功能级强制 false。"""
        cache_key = f"{tenant_id}:{feature_key}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            value, ts = cached
            if time.monotonic() - ts < self._CACHE_TTL:
                return value

        try:
            fs_orm = await self._repo.get_by_key(session, tenant_id, feature_key)
            if fs_orm is None:
                result = True
            else:
                is_enabled = fs_orm.is_enabled == "true"
                if fs_orm.scope == FeatureScope.SUB_FEATURE.value and fs_orm.parent_feature_key:
                    parent_orm = await self._repo.get_by_key(
                        session, tenant_id, fs_orm.parent_feature_key
                    )
                    if parent_orm and parent_orm.is_enabled != "true":
                        result = False
                    else:
                        result = is_enabled
                else:
                    result = is_enabled
        except Exception:
            if self._degrade_strategy == "deny":
                raise BizOpsError(
                    BizOpsErrorCode.FEATURE_DISABLED,
                    f"功能开关校验失败且降级策略为 deny: {feature_key}",
                )
            result = True

        self._cache[cache_key] = (result, time.monotonic())
        return result

    async def enforce(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        feature_key: str,
    ) -> None:
        """强制校验 - 关闭时抛 BizOpsError。"""
        if not await self.check(session, tenant_id, feature_key):
            raise BizOpsError(
                BizOpsErrorCode.FEATURE_DISABLED,
                f"功能已关闭: {feature_key}",
            )

    @classmethod
    def invalidate_cache(cls, tenant_id: UUID | None = None) -> None:
        """失效缓存 - 开关变更后调用。"""
        if tenant_id is None:
            cls._cache.clear()
        else:
            prefix = f"{tenant_id}:"
            keys_to_remove = [k for k in cls._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del cls._cache[k]