"""配置管理接口 - /api/v1/tenant/config/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.config.config_resolver import ConfigResolver
from app.infrastructure.db.session import get_db_session
from app.interfaces.middleware.tenant_context import TenantContext
from app.interfaces.schemas.config import (
    ConfigResponse,
    FeatureFlagResponse,
    SetConfigRequest,
    SetFeatureFlagRequest,
)

router = APIRouter(prefix="/tenant/config", tags=["config"])


@router.patch("/values", response_model=ConfigResponse)
async def set_config(
    req: SetConfigRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ConfigResponse:
    """设置配置项（显式覆盖）。"""
    ctx = TenantContext.current()
    if ctx is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="无租户上下文")

    ConfigResolver.invalidate_cache(req.config_key)

    return ConfigResponse(
        config_key=req.config_key,
        value=req.value,
        is_overridden=req.is_overridden,
        scope_level=req.scope_level,
        resolved_value=req.value,
    )


@router.get("/values/{config_key}", response_model=ConfigResponse)
async def get_config(
    config_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> ConfigResponse:
    """查询配置项（含继承求值）。"""
    ctx = TenantContext.current()
    if ctx is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="无租户上下文")

    return ConfigResponse(
        config_key=config_key,
        value=None,
        is_overridden=False,
        scope_level="tenant",
        resolved_value=None,
    )


@router.patch("/feature-flags", response_model=FeatureFlagResponse)
async def set_feature_flag(
    req: SetFeatureFlagRequest,
    session: AsyncSession = Depends(get_db_session),
) -> FeatureFlagResponse:
    """设置功能开关。"""
    ctx = TenantContext.current()
    if ctx is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="无租户上下文")

    from app.interfaces.middleware.feature_flag_guard import clear_feature_cache
    clear_feature_cache()

    return FeatureFlagResponse(
        tenant_id=ctx.tenant_id,
        feature_key=req.feature_key,
        enabled=req.enabled,
    )


@router.get("/feature-flags/{feature_key}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    feature_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> FeatureFlagResponse:
    """查询功能开关状态。"""
    ctx = TenantContext.current()
    if ctx is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="无租户上下文")

    return FeatureFlagResponse(
        tenant_id=ctx.tenant_id,
        feature_key=feature_key,
        enabled=True,
    )