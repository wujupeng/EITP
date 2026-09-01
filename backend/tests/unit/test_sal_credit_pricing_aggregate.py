"""SAL CreditLimit / CustomerPricing 聚合 + CreditControlService / PriceMatchService 单元测试。

覆盖信用额度占用/释放/可用额度/并发版本号、超信用策略 BLOCK/WARN/SPECIAL_APPROVAL、
价格体系优先级与有效期校验、PriceMatchService 按优先级匹配（促销>协议>折扣>标准）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.sales.aggregates.credit_limit_aggregate import CreditLimitAggregate
from app.domain.sales.aggregates.customer_pricing_aggregate import (
    CustomerPricingAggregate,
    PricingStatus,
)
from app.domain.sales.services.credit_control_service import CreditControlService
from app.domain.sales.services.price_match_service import PriceMatchService
from app.domain.sales.value_objects.credit_pricing_vo import (
    OverCreditStrategy,
    PricePriority,
    PriceType,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


def _credit(total: float = 10000.0, used: float = 0.0) -> CreditLimitAggregate:
    return CreditLimitAggregate(total_limit=total, used_amount=used)


def _published_pricing(
    sku_id: uuid4,
    price_type: PriceType,
    agreement_price: float | None = None,
    discount_rate: float | None = None,
    customer_id: uuid4 | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> CustomerPricingAggregate:
    now = datetime.now(timezone.utc)
    p = CustomerPricingAggregate(
        enterprise_sku_id=sku_id,
        price_type=price_type,
        agreement_price=agreement_price,
        discount_rate=discount_rate,
        customer_id=customer_id,
        valid_from=valid_from or now,
        valid_until=valid_until,
    )
    p.submit()
    p.approve(uuid4())
    p.publish()
    return p


class CreditLimitAggregateTest:
    """CreditLimitAggregate 信用额度占用/释放与不变量测试。"""

    def test_available_amount_calculation(self) -> None:
        cl = _credit(total=10000, used=3000)
        assert cl.available_amount == 7000.0

    def test_zero_limit_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            CreditLimitAggregate(total_limit=0)
        assert exc.value.code == SALErrorCode.CREDIT_CONFIG_NOT_FOUND

    def test_negative_used_rejected(self) -> None:
        with pytest.raises(SALError) as exc:
            CreditLimitAggregate(total_limit=1000, used_amount=-1)
        assert exc.value.code == SALErrorCode.CREDIT_CONCURRENT_CONFLICT

    def test_check_pass_when_within_limit(self) -> None:
        cl = _credit(total=10000, used=3000)
        result = cl.check(5000)
        assert result.is_pass is True
        assert result.is_over_credit is False
        assert result.after_used == 8000.0

    def test_check_block_strategy_when_over(self) -> None:
        cl = _credit(total=10000, used=8000)
        result = cl.check(3000)
        assert result.is_over_credit is True
        assert result.result == "block"
        assert result.strategy == OverCreditStrategy.BLOCK

    def test_check_warn_strategy(self) -> None:
        cl = CreditLimitAggregate(
            total_limit=10000, used_amount=8000, over_credit_strategy=OverCreditStrategy.WARN
        )
        result = cl.check(3000)
        assert result.result == "warn"

    def test_check_special_approval_strategy(self) -> None:
        cl = CreditLimitAggregate(
            total_limit=10000,
            used_amount=8000,
            over_credit_strategy=OverCreditStrategy.SPECIAL_APPROVAL,
        )
        result = cl.check(3000)
        assert result.result == "special_approval"

    def test_check_negative_amount_rejected(self) -> None:
        cl = _credit()
        with pytest.raises(SALError) as exc:
            cl.check(-1)
        assert exc.value.code == SALErrorCode.CREDIT_CONCURRENT_CONFLICT

    def test_occupy_increases_used_and_version(self) -> None:
        cl = _credit(total=10000)
        v0 = cl.version
        cl.occupy(3000)
        assert cl.used_amount == 3000.0
        assert cl.version == v0 + 1

    def test_occupy_block_strategy_raises_when_over(self) -> None:
        cl = _credit(total=10000, used=8000)
        with pytest.raises(SALError) as exc:
            cl.occupy(3000)
        assert exc.value.code == SALErrorCode.CREDIT_LIMIT_EXCEEDED
        assert cl.used_amount == 8000  # 未占用

    def test_occupy_warn_strategy_succeeds_when_over(self) -> None:
        cl = CreditLimitAggregate(
            total_limit=10000, used_amount=8000, over_credit_strategy=OverCreditStrategy.WARN
        )
        cl.occupy(3000)
        assert cl.used_amount == 11000.0

    def test_release_decreases_used_and_increases_version(self) -> None:
        cl = _credit(total=10000, used=5000)
        v0 = cl.version
        cl.release(2000)
        assert cl.used_amount == 3000.0
        assert cl.version == v0 + 1

    def test_release_more_than_used_rejected(self) -> None:
        cl = _credit(total=10000, used=1000)
        with pytest.raises(SALError) as exc:
            cl.release(2000)
        assert exc.value.code == SALErrorCode.CREDIT_CONCURRENT_CONFLICT

    def test_release_negative_rejected(self) -> None:
        cl = _credit(total=10000, used=1000)
        with pytest.raises(SALError) as exc:
            cl.release(-1)
        assert exc.value.code == SALErrorCode.CREDIT_CONCURRENT_CONFLICT

    def test_occupy_release_roundtrip(self) -> None:
        cl = _credit(total=10000)
        cl.occupy(4000)
        cl.release(4000)
        assert cl.used_amount == 0.0
        assert cl.available_amount == 10000.0


class CreditControlServiceTest:
    """CreditControlService 信用控制领域服务测试。"""

    def test_check_delegates_to_aggregate(self) -> None:
        cl = _credit(total=10000, used=2000)
        result = CreditControlService.check(cl, 3000)
        assert result.is_pass is True

    def test_occupy_positive_amount(self) -> None:
        cl = _credit(total=10000)
        CreditControlService.occupy(cl, 5000)
        assert cl.used_amount == 5000.0

    def test_occupy_non_positive_rejected(self) -> None:
        cl = _credit(total=10000)
        with pytest.raises(SALError) as exc:
            CreditControlService.occupy(cl, 0)
        assert exc.value.code == SALErrorCode.CREDIT_CONCURRENT_CONFLICT

    def test_release_positive_amount(self) -> None:
        cl = _credit(total=10000, used=5000)
        CreditControlService.release(cl, 2000)
        assert cl.used_amount == 3000.0

    def test_release_non_positive_rejected(self) -> None:
        cl = _credit(total=10000, used=5000)
        with pytest.raises(SALError) as exc:
            CreditControlService.release(cl, 0)
        assert exc.value.code == SALErrorCode.CREDIT_CONCURRENT_CONFLICT

    def test_evaluate_with_override_strategy_warn(self) -> None:
        cl = _credit(total=10000, used=8000)  # 默认 BLOCK
        result = CreditControlService.evaluate(cl, 3000, OverCreditStrategy.WARN)
        assert result.result == "warn"
        # 评估不应改变聚合的策略
        assert cl.over_credit_strategy == OverCreditStrategy.BLOCK

    def test_evaluate_without_override_uses_aggregate_strategy(self) -> None:
        cl = _credit(total=10000, used=8000)
        result = CreditControlService.evaluate(cl, 3000)
        assert result.result == "block"


class CustomerPricingAggregateTest:
    """CustomerPricingAggregate 价格体系优先级与有效期测试。"""

    def test_priority_from_price_type(self) -> None:
        assert PricePriority.from_price_type(PriceType.PROMOTION).value == 1
        assert PricePriority.from_price_type(PriceType.AGREEMENT).value == 2
        assert PricePriority.from_price_type(PriceType.DISCOUNT).value == 3
        assert PricePriority.from_price_type(PriceType.STANDARD).value == 4

    def test_priority_ordering(self) -> None:
        promo = PricePriority(1)
        std = PricePriority(4)
        assert promo < std
        assert promo <= std

    def test_valid_until_before_from_rejected(self) -> None:
        now = datetime.now(timezone.utc)
        with pytest.raises(SALError) as exc:
            CustomerPricingAggregate(
                enterprise_sku_id=uuid4(),
                valid_from=now,
                valid_until=now - timedelta(days=1),
            )
        assert exc.value.code == SALErrorCode.PRICING_NOT_FOUND

    def test_full_lifecycle_to_published(self) -> None:
        p = CustomerPricingAggregate(enterprise_sku_id=uuid4(), price_type=PriceType.STANDARD)
        p.submit()
        p.approve(uuid4())
        p.publish()
        assert p.status == PricingStatus.PUBLISHED
        assert p.is_published is True

    def test_reject_from_submitted_terminal(self) -> None:
        p = CustomerPricingAggregate(enterprise_sku_id=uuid4())
        p.submit()
        p.reject(uuid4())
        assert p.status == PricingStatus.REJECTED
        with pytest.raises(SALError) as exc:
            p.submit()
        assert exc.value.code == SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION

    def test_check_effective_requires_published(self) -> None:
        p = CustomerPricingAggregate(enterprise_sku_id=uuid4())
        assert p.check_effective() is False

    def test_check_effective_within_period(self) -> None:
        now = datetime.now(timezone.utc)
        p = _published_pricing(
            uuid4(), PriceType.AGREEMENT, agreement_price=80.0,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        assert p.check_effective(now) is True

    def test_check_effective_after_valid_until(self) -> None:
        now = datetime.now(timezone.utc)
        p = _published_pricing(
            uuid4(), PriceType.AGREEMENT, agreement_price=80.0,
            valid_from=now - timedelta(days=2), valid_until=now - timedelta(days=1),
        )
        assert p.check_effective(now) is False

    def test_check_effective_before_valid_from(self) -> None:
        now = datetime.now(timezone.utc)
        p = _published_pricing(
            uuid4(), PriceType.AGREEMENT, agreement_price=80.0,
            valid_from=now + timedelta(days=1), valid_until=now + timedelta(days=2),
        )
        assert p.check_effective(now) is False

    def test_final_unit_price_returns_agreement_price(self) -> None:
        p = CustomerPricingAggregate(
            enterprise_sku_id=uuid4(),
            price_type=PriceType.AGREEMENT,
            agreement_price=88.0,
        )
        assert p.final_unit_price == 88.0


class PriceMatchServiceTest:
    """PriceMatchService 按优先级匹配价格测试（促销>协议>折扣>标准）。"""

    def test_standard_price_must_be_positive(self) -> None:
        with pytest.raises(SALError) as exc:
            PriceMatchService.match([], None, [], uuid4(), 0.0)
        assert exc.value.code == SALErrorCode.PRICING_NOT_FOUND

    def test_no_candidates_returns_standard(self) -> None:
        result = PriceMatchService.match([], None, [], uuid4(), 100.0)
        assert result.matched_price_type == PriceType.STANDARD
        assert result.final_unit_price == 100.0
        assert result.priority.value == 4

    def test_promotion_beats_agreement(self) -> None:
        sku = uuid4()
        now = datetime.now(timezone.utc)
        promo = _published_pricing(
            sku, PriceType.PROMOTION, agreement_price=70.0,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        agreement = _published_pricing(
            sku, PriceType.AGREEMENT, agreement_price=80.0,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        result = PriceMatchService.match([agreement, promo], None, [], sku, 100.0, now)
        assert result.matched_price_type == PriceType.PROMOTION
        assert result.final_unit_price == 70.0

    def test_agreement_beats_discount(self) -> None:
        sku = uuid4()
        now = datetime.now(timezone.utc)
        agreement = _published_pricing(
            sku, PriceType.AGREEMENT, agreement_price=80.0,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        discount = _published_pricing(
            sku, PriceType.DISCOUNT, discount_rate=0.85,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        result = PriceMatchService.match([discount, agreement], None, [], sku, 100.0, now)
        assert result.matched_price_type == PriceType.AGREEMENT
        assert result.final_unit_price == 80.0

    def test_discount_uses_standard_price_when_no_agreement(self) -> None:
        sku = uuid4()
        now = datetime.now(timezone.utc)
        discount = _published_pricing(
            sku, PriceType.DISCOUNT, discount_rate=0.85,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        result = PriceMatchService.match([discount], None, [], sku, 100.0, now)
        assert result.matched_price_type == PriceType.DISCOUNT
        assert result.final_unit_price == 85.0

    def test_customer_specific_pricing_matches(self) -> None:
        sku = uuid4()
        cust = uuid4()
        now = datetime.now(timezone.utc)
        p = _published_pricing(
            sku, PriceType.AGREEMENT, agreement_price=75.0, customer_id=cust,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        result = PriceMatchService.match([p], cust, [], sku, 100.0, now)
        assert result.matched_price_type == PriceType.AGREEMENT
        assert result.final_unit_price == 75.0

    def test_customer_specific_pricing_skipped_for_other_customer(self) -> None:
        sku = uuid4()
        now = datetime.now(timezone.utc)
        p = _published_pricing(
            sku, PriceType.AGREEMENT, agreement_price=75.0, customer_id=uuid4(),
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        result = PriceMatchService.match([p], uuid4(), [], sku, 100.0, now)
        assert result.matched_price_type == PriceType.STANDARD

    def test_expired_pricing_skipped(self) -> None:
        sku = uuid4()
        now = datetime.now(timezone.utc)
        expired = _published_pricing(
            sku, PriceType.AGREEMENT, agreement_price=70.0,
            valid_from=now - timedelta(days=2), valid_until=now - timedelta(days=1),
        )
        result = PriceMatchService.match([expired], None, [], sku, 100.0, now)
        assert result.matched_price_type == PriceType.STANDARD

    def test_different_sku_skipped(self) -> None:
        sku = uuid4()
        other_sku = uuid4()
        now = datetime.now(timezone.utc)
        p = _published_pricing(
            other_sku, PriceType.AGREEMENT, agreement_price=70.0,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        result = PriceMatchService.match([p], None, [], sku, 100.0, now)
        assert result.matched_price_type == PriceType.STANDARD

    def test_category_not_matched_skipped(self) -> None:
        sku = uuid4()
        now = datetime.now(timezone.utc)
        p = _published_pricing(
            sku, PriceType.AGREEMENT, agreement_price=70.0, customer_id=None,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        p.category_id = uuid4()  # 绑定到某分类
        result = PriceMatchService.match([p], None, [], sku, 100.0, now)
        assert result.matched_price_type == PriceType.STANDARD

    def test_category_matched_pricing_used(self) -> None:
        sku = uuid4()
        cat_id = uuid4()
        now = datetime.now(timezone.utc)
        p = _published_pricing(
            sku, PriceType.AGREEMENT, agreement_price=75.0,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        p.category_id = cat_id
        result = PriceMatchService.match([p], None, [cat_id], sku, 100.0, now)
        assert result.matched_price_type == PriceType.AGREEMENT
        assert result.final_unit_price == 75.0

    def test_agreement_price_non_positive_falls_back_to_standard(self) -> None:
        sku = uuid4()
        now = datetime.now(timezone.utc)
        p = _published_pricing(
            sku, PriceType.AGREEMENT, agreement_price=0.0,
            valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1),
        )
        result = PriceMatchService.match([p], None, [], sku, 100.0, now)
        assert result.matched_price_type == PriceType.STANDARD
        assert result.final_unit_price == 100.0