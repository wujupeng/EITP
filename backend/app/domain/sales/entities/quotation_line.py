"""SAL QuotationLine 实体 - 报价行，SalesQuotationAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import SALError, SALErrorCode


@dataclass
class QuotationLine:
    """报价行实体 - 引用 MDM EnterpriseSKU，行金额系统计算。"""

    line_id: UUID = field(default_factory=uuid4)
    quotation_id: UUID = field(default_factory=uuid4)
    enterprise_sku_id: UUID = field(default_factory=uuid4)
    quantity: float = 0.0
    unit_price: float = 0.0
    lead_time_days: int = 0
    remark: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise SALError(SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION, "报价数量必须为正数")
        if self.unit_price <= 0:
            raise SALError(SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION, "报价单价必须为正数")

    @property
    def line_amount(self) -> float:
        """行金额 = quantity × unit_price，系统计算。"""
        return round(self.quantity * self.unit_price, 2)