"""BIZ-OPS 策略配置路由 - 功能开关管理 + 业务规则配置 API。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.biz_ops.feature_switch_guard import FeatureSwitchGuard
from app.application.biz_ops.strategy_config_app_svc import StrategyConfigAppSvc
from app.domain.biz_ops.aggregates.feature_switch_aggregate import FeatureSwitchAggregate
from app.domain.biz_ops.enums.enums import FeatureScope
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.repositories.feature_switch_repository import (
    FeatureSwitchRepository,
)
from app.infrastructure.db.session import get_db_session
from app.interfaces.api.v1.biz_ops.schemas.feature_switch_schemas import (
    FeatureSwitchCreateRequest,
    FeatureSwitchResponse,
    FeatureSwitchUpdateRequest,
)
from app.interfaces.api.v1.biz_ops.schemas.business_rule_schema import (
    BusinessRuleCreateRequest,
    BusinessRuleResponse,
    BusinessRuleUpdateRequest,
)
from app.interfaces.api.v1.biz_ops.schemas.pricing_strategy_schema import (
    PricingStrategyCreateRequest,
    PricingStrategyResponse,
    PricingStrategyUpdateRequest,
)
from app.interfaces.api.v1.biz_ops.schemas.tax_config_schema import (
    TaxConfigCreateRequest,
    TaxConfigUpdateRequest,
)
from app.interfaces.api.v1.biz_ops.schemas.inventory_strategy_schema import (
    InventoryStrategyCreateRequest,
    InventoryStrategyUpdateRequest,
)
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode
from app.interfaces.middleware.security_context import SecurityContext

router = APIRouter(prefix="/biz-ops/strategies/feature-switches", tags=["biz-ops-feature-switches"])


def _get_tenant_id() -> UUID:
    ctx = SecurityContext.current()
    if ctx is None:
        raise BizOpsError(BizOpsErrorCode.INTERNAL_ERROR, "安全上下文缺失")
    tid = ctx.tenant.tenant_id
    return UUID(str(tid)) if isinstance(tid, str) else tid


def _get_user_id() -> UUID:
    ctx = SecurityContext.current()
    if ctx is None:
        raise BizOpsError(BizOpsErrorCode.INTERNAL_ERROR, "安全上下文缺失")
    uid = ctx.user.user_id
    return UUID(str(uid)) if isinstance(uid, str) else uid


@router.get("", response_model=list[FeatureSwitchResponse])
async def list_feature_switches(
    session: AsyncSession = Depends(get_db_session),
) -> list[FeatureSwitchResponse]:
    tenant_id = _get_tenant_id()
    repo = FeatureSwitchRepository()
    orm_list = await repo.list_by_tenant(session, tenant_id)
    guard = FeatureSwitchGuard()
    results: list[FeatureSwitchResponse] = []
    for orm in orm_list:
        agg = repo.to_aggregate(orm)
        parent_orm = None
        if agg.parent_feature_key:
            parent_orm = await repo.get_by_key(session, tenant_id, agg.parent_feature_key)
        parent_agg = repo.to_aggregate(parent_orm) if parent_orm else None
        effective = agg.resolve_effective(parent_agg)
        results.append(
            FeatureSwitchResponse(
                id=orm.id,
                tenant_id=orm.tenant_id,
                feature_key=orm.feature_key,
                scope=orm.scope,
                is_enabled=agg.is_enabled,
                parent_feature_key=orm.parent_feature_key,
                description=orm.description,
                effective_is_enabled=effective,
            )
        )
    return results


@router.get("/{feature_key}", response_model=FeatureSwitchResponse)
async def get_feature_switch(
    feature_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> FeatureSwitchResponse:
    tenant_id = _get_tenant_id()
    repo = FeatureSwitchRepository()
    orm = await repo.get_by_key(session, tenant_id, feature_key)
    if orm is None:
        raise BizOpsError(BizOpsErrorCode.FEATURE_NOT_FOUND, f"功能开关不存在: {feature_key}")
    agg = repo.to_aggregate(orm)
    parent_orm = None
    if agg.parent_feature_key:
        parent_orm = await repo.get_by_key(session, tenant_id, agg.parent_feature_key)
    parent_agg = repo.to_aggregate(parent_orm) if parent_orm else None
    effective = agg.resolve_effective(parent_agg)
    return FeatureSwitchResponse(
        id=orm.id,
        tenant_id=orm.tenant_id,
        feature_key=orm.feature_key,
        scope=orm.scope,
        is_enabled=agg.is_enabled,
        parent_feature_key=orm.parent_feature_key,
        description=orm.description,
        effective_is_enabled=effective,
    )


@router.put("/{feature_key}", response_model=FeatureSwitchResponse)
async def update_feature_switch(
    feature_key: str,
    req: FeatureSwitchUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> FeatureSwitchResponse:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    repo = FeatureSwitchRepository()
    orm = await repo.get_by_key(session, tenant_id, feature_key)
    if orm is None:
        raise BizOpsError(BizOpsErrorCode.FEATURE_NOT_FOUND, f"功能开关不存在: {feature_key}")
    agg = repo.to_aggregate(orm)
    new_agg = agg.toggle(req.is_enabled, user_id)
    updated_orm = await repo.upsert(session, new_agg)
    await session.commit()
    FeatureSwitchGuard.invalidate_cache(tenant_id)
    return FeatureSwitchResponse(
        id=updated_orm.id,
        tenant_id=updated_orm.tenant_id,
        feature_key=updated_orm.feature_key,
        scope=updated_orm.scope,
        is_enabled=new_agg.is_enabled,
        parent_feature_key=updated_orm.parent_feature_key,
        description=updated_orm.description,
        effective_is_enabled=new_agg.is_enabled,
    )


@router.post("", response_model=FeatureSwitchResponse, status_code=201)
async def create_feature_switch(
    req: FeatureSwitchCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> FeatureSwitchResponse:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    repo = FeatureSwitchRepository()
    existing = await repo.get_by_key(session, tenant_id, req.feature_key)
    if existing:
        raise BizOpsError(BizOpsErrorCode.FEATURE_KEY_FORMAT_INVALID, f"功能开关已存在: {req.feature_key}")
    agg = FeatureSwitchAggregate(
        id=EntityId.generate(),
        tenant_id=tenant_id,
        feature_key=req.feature_key,
        scope=FeatureScope(req.scope),
        is_enabled=req.is_enabled,
        parent_feature_key=req.parent_feature_key,
        description=req.description,
        updated_by=user_id,
    )
    orm = await repo.create(session, agg)
    await session.commit()
    FeatureSwitchGuard.invalidate_cache(tenant_id)
    return FeatureSwitchResponse(
        id=orm.id,
        tenant_id=orm.tenant_id,
        feature_key=orm.feature_key,
        scope=orm.scope,
        is_enabled=agg.is_enabled,
        parent_feature_key=orm.parent_feature_key,
        description=orm.description,
        effective_is_enabled=agg.is_enabled,
    )


# ==================== 业务规则 API ====================

rule_router = APIRouter(prefix="/biz-ops/strategies/business-rules", tags=["biz-ops-business-rules"])


@rule_router.post("", status_code=201)
async def create_business_rule(
    req: BusinessRuleCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.create_rule(tenant_id, user_id, req.model_dump())


@rule_router.get("")
async def list_business_rules(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.list_rules(tenant_id)


@rule_router.put("/{rule_key}")
async def update_business_rule(
    rule_key: str,
    req: BusinessRuleUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.update_rule(tenant_id, rule_key, req.model_dump(exclude_none=True))


@rule_router.post("/{rule_key}/activate")
async def activate_business_rule(
    rule_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.activate_rule(tenant_id, rule_key)


@rule_router.post("/{rule_key}/deactivate")
async def deactivate_business_rule(
    rule_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.deactivate_rule(tenant_id, rule_key)


# ==================== 定价策略 API ====================

pricing_router = APIRouter(prefix="/biz-ops/strategies/pricing", tags=["biz-ops-pricing"])


@pricing_router.post("", status_code=201)
async def create_pricing_strategy(
    req: PricingStrategyCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.create_pricing_strategy(tenant_id, user_id, req.model_dump())


@pricing_router.get("")
async def list_pricing_strategies(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.list_pricing_strategies(tenant_id)


@pricing_router.get("/{strategy_key}")
async def get_pricing_strategy(
    strategy_key: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.get_pricing_strategy(tenant_id, strategy_key)


@pricing_router.put("/{strategy_key}")
async def update_pricing_strategy(
    strategy_key: str,
    req: PricingStrategyUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.update_pricing_strategy(tenant_id, strategy_key, req.model_dump(exclude_none=True))


# ==================== 税务配置 API ====================

tax_router = APIRouter(prefix="/biz-ops/strategies/tax-configs", tags=["biz-ops-tax"])


@tax_router.post("", status_code=201)
async def create_tax_config(
    req: TaxConfigCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.create_tax_config(tenant_id, req.model_dump())


@tax_router.get("")
async def list_tax_configs(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.list_tax_configs(tenant_id)


@tax_router.put("/{config_key}")
async def update_tax_config(
    config_key: str,
    req: TaxConfigUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.update_tax_config(tenant_id, config_key, req.model_dump(exclude_none=True))


# ==================== 库存策略 API ====================

inv_strategy_router = APIRouter(prefix="/biz-ops/strategies/inventory-strategies", tags=["biz-ops-inv-strategy"])


@inv_strategy_router.post("", status_code=201)
async def create_inventory_strategy(
    req: InventoryStrategyCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.create_inventory_strategy(tenant_id, req.model_dump())


@inv_strategy_router.get("")
async def list_inventory_strategies(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.list_inventory_strategies(tenant_id)


@inv_strategy_router.put("/{strategy_key}")
async def update_inventory_strategy(
    strategy_key: str,
    req: InventoryStrategyUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    tenant_id = _get_tenant_id()
    svc = StrategyConfigAppSvc(session)
    return await svc.update_inventory_strategy(tenant_id, strategy_key, req.model_dump(exclude_none=True))