"""SAL PriceMatchService 领域服务 - 价格匹配，按优先级（促销>协议>折扣>标准）匹配。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.sales.aggregates.customer_pricing_aggregate import CustomerPricingAggregate
from app.domain.sales.value_objects.credit_pricing_vo import (
    PriceType,
    PricingMatchResult,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


class PriceMatchService:
    """价格匹配领域服务。

    输入：(customer_id, category_ids, enterprise_sku_id, 标准价)
    输出：PricingMatchResult
    核心逻辑：按优先级查询（促销价 > 协议价 > 折扣 > 标准价）
            + 有效期过滤（valid_from ≤ today ≤ valid_until）
            + 审批状态过滤（仅 PUBLISHED）
            + 记录匹配结果，无匹配则返回标准价。
    """

    @staticmethod
    def match(
        pricings: list[CustomerPricingAggregate],
        customer_id: UUID | None,
        category_ids: list[UUID],
        enterprise_sku_id: UUID,
        standard_price: float,
        now: datetime | None = None,
    ) -> PricingMatchResult:
        if standard_price <= 0:
            raise SALError(SALErrorCode.PRICING_NOT_FOUND, "标准价必须为正数")
        now = now or datetime.now(timezone.utc)

        # 过滤：同 SKU + 已发布 + 有效期内 + 客户或分类匹配
        candidates: list[CustomerPricingAggregate] = []
        for p in pricings:
            if p.enterprise_sku_id != enterprise_sku_id:
                continue
            if not p.check_effective(now):
                continue
            if p.customer_id is not None and p.customer_id != customer_id:
                continue
            if p.category_id is not None and p.category_id not in category_ids:
                continue
            candidates.append(p)

        if not candidates:
            return PricingMatchResult.standard(standard_price)

        # 按优先级排序（priority.value 越小优先级越高）
        candidates.sort(key=lambda p: p.priority.value)
        best = candidates[0]
        final_price = best.final_unit_price
        if final_price is None or final_price <= 0:
            # 折扣类型需配合标准价
            if best.price_type == PriceType.DISCOUNT and best.discount_rate is not None:
                final_price = round(standard_price * best.discount_rate, 2)
            else:
                return PricingMatchResult.standard(standard_price)

        return PricingMatchResult(
            matched_price_type=best.price_type,
            final_unit_price=final_price,
            priority=best.priority,
            matched_pricing_id=best.pricing_id,
        )