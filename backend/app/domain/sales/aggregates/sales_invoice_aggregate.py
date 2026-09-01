"""SAL SalesInvoiceAggregate 聚合根 - 销售发票，含匹配状态。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.entities.invoice_line import InvoiceLine
from app.domain.sales.value_objects.settlement_vo import InvoiceStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


@dataclass
class SalesInvoiceAggregate:
    """销售发票聚合根 - 禁止贫血模型。

    发票金额校验 + 与销售结算单匹配 + 匹配差异阈值校验。
    状态：PENDING/MATCHED/MISMATCHED。
    """

    invoice_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    invoice_code: str = ""
    customer_id: UUID = field(default_factory=uuid4)
    invoice_amount: float = 0.0
    tax_amount: float = 0.0
    invoice_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lines: list[InvoiceLine] = field(default_factory=list)
    matched_settlement_id: UUID | None = None
    status: InvoiceStatus = InvoiceStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.invoice_amount < 0:
            raise SALError(SALErrorCode.INVOICE_NOT_FOUND, "发票金额不可为负")
        if self.tax_amount < 0:
            raise SALError(SALErrorCode.INVOICE_NOT_FOUND, "税额不可为负")

    def add_line(self, line: InvoiceLine) -> None:
        """添加发票行。"""
        line.invoice_id = self.invoice_id
        self.lines.append(line)
        self.invoice_amount = round(self.invoice_amount + line.amount, 2)
        self.updated_at = datetime.now(timezone.utc)

    def match(self, settlement_id: UUID, expected_amount: float, threshold: float) -> None:
        """匹配结算单 - 差异阈值校验。"""
        if self.status != InvoiceStatus.PENDING:
            raise SALError(SALErrorCode.INVOICE_NOT_FOUND, "发票非待匹配状态")
        diff = abs(self.invoice_amount - expected_amount)
        if diff > threshold:
            self.status = InvoiceStatus.MISMATCHED
            raise SALError(
                SALErrorCode.INVOICE_MATCH_DIFF_EXCEEDED,
                f"发票匹配差异超阈值: |{self.invoice_amount} - {expected_amount}|"
                f" = {diff} > {threshold}",
            )
        self.status = InvoiceStatus.MATCHED
        self.matched_settlement_id = settlement_id
        self.updated_at = datetime.now(timezone.utc)

    @property
    def total_amount_with_tax(self) -> float:
        """价税合计。"""
        return round(self.invoice_amount + self.tax_amount, 2)

    @property
    def is_matched(self) -> bool:
        return self.status == InvoiceStatus.MATCHED