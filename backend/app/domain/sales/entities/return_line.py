"""SAL ReturnLine 实体 - 退货行，SalesReturnAggregate 内部实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.value_objects.sales_return_vo import Disposition, QcResult
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


@dataclass
class ReturnLine:
    """退货行实体 - 退货数量校验（不超原发货可用量 = 已发 - 已退）。"""

    line_id: UUID = field(default_factory=uuid4)
    return_id: UUID = field(default_factory=uuid4)
    original_shipment_line_id: UUID = field(default_factory=uuid4)
    enterprise_sku_id: UUID = field(default_factory=uuid4)
    return_quantity: float = 0.0
    unit_price: float = 0.0
    qc_result: QcResult | None = None
    disposition: Disposition | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.return_quantity <= 0:
            raise SALError(SALErrorCode.RETURN_OVER_RETURNED, "退货数量必须为正数")
        if self.unit_price < 0:
            raise SALError(SALErrorCode.RETURN_OVER_RETURNED, "退货单价不可为负")

    @property
    def refund_amount(self) -> float:
        """退款金额 = 退货数量 × 原销售单价。"""
        return round(self.return_quantity * self.unit_price, 2)

    def record_qc(self, qc_result: QcResult) -> None:
        """录入 QC 结论。"""
        self.qc_result = qc_result

    def dispose(self, disposition: Disposition) -> None:
        """处置决策 - Restock/Quarantine/Scrap。"""
        if self.qc_result is None:
            raise SALError(SALErrorCode.RETURN_NOT_APPROVED, "未录入 QC 结论不可处置")
        self.disposition = disposition