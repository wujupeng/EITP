"""SAL CustomerPricingAggregate 聚合根 - 客户价格体系，含匹配优先级 + 治理工作流审批。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.domain.sales.value_objects.credit_pricing_vo import PricePriority, PriceType
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


class PricingStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"
    EXPIRED = "expired"


_VALID_TRANSITIONS: dict[PricingStatus, set[PricingStatus]] = {
    PricingStatus.DRAFT: {PricingStatus.SUBMITTED},
    PricingStatus.SUBMITTED: {PricingStatus.APPROVED, PricingStatus.REJECTED},
    PricingStatus.APPROVED: {PricingStatus.PUBLISHED},
    PricingStatus.PUBLISHED: {PricingStatus.EXPIRED},
    PricingStatus.REJECTED: set(),
    PricingStatus.EXPIRED: set(),
}


@dataclass
class CustomerPricingAggregate:
    """客户价格体系聚合根 - 禁止贫血模型。

    价格类型 ∈ {AGREEMENT/DISCOUNT/PROMOTION/STANDARD}。
    匹配优先级：促销 1 > 协议 2 > 折扣 3 > 标准 4。
    有效期校验：valid_until ≥ valid_from。
    """

    pricing_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    customer_id: UUID | None = None
    category_id: UUID | None = None
    enterprise_sku_id: UUID = field(default_factory=uuid4)
    price_type: PriceType = PriceType.STANDARD
    agreement_price: float | None = None
    discount_rate: float | None = None
    promotion_id: UUID | None = None
    priority: PricePriority = field(default_factory=lambda: PricePriority(4))
    valid_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime | None = None
    status: PricingStatus = PricingStatus.DRAFT
    governance_state: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.priority = PricePriority.from_price_type(self.price_type)
        if self.valid_until and self.valid_until < self.valid_from:
            raise SALError(SALErrorCode.PRICING_NOT_FOUND, "有效期结束日期早于开始日期")

    def _transition(self, target: PricingStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise SALError(
                SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION,
                f"价格体系状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def submit(self) -> None:
        self._transition(PricingStatus.SUBMITTED)
        self.governance_state = "submitted"

    def approve(self, approver_id: UUID, opinion: str = "") -> None:
        self._transition(PricingStatus.APPROVED)
        self.governance_state = "approved"

    def reject(self, approver_id: UUID, opinion: str = "") -> None:
        self._transition(PricingStatus.REJECTED)
        self.governance_state = "rejected"

    def publish(self) -> None:
        self._transition(PricingStatus.PUBLISHED)
        self.governance_state = "published"

    def check_effective(self, date: datetime | None = None) -> bool:
        """校验在指定日期是否有效：已发布 + 在有效期内。"""
        if self.status != PricingStatus.PUBLISHED:
            return False
        now = date or datetime.now(timezone.utc)
        if now < self.valid_from:
            return False
        return not (self.valid_until and now > self.valid_until)

    @property
    def final_unit_price(self) -> float | None:
        """获取最终单价：协议价直接返回，折扣率需配合标准价使用。"""
        if self.price_type == PriceType.AGREEMENT or self.price_type == PriceType.PROMOTION:
            return self.agreement_price
        return self.agreement_price

    @property
    def is_published(self) -> bool:
        return self.status == PricingStatus.PUBLISHED