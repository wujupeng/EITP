"""SAL 结算值对象 - SettlementStatus/InvoiceStatus/PaymentStatus/PaymentMethod/SalesRevenue。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SettlementStatus(str, Enum):
    PENDING = "pending"
    RECONCILED = "reconciled"
    INVOICE_MATCHED = "invoice_matched"
    PAYMENT_REQUESTED = "payment_requested"
    PAYMENT_COMPLETED = "payment_completed"


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    MISMATCHED = "mismatched"


class PaymentStatus(str, Enum):
    REQUESTED = "requested"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    CASH = "cash"
    OTHER = "other"


@dataclass(frozen=True)
class SalesRevenue:
    """销售收入值对象 - revenue = unit_price × qty，cost = moving_avg_cost × qty。

    通过 INV Financial/Revenue API 落地（红线二）。
    """

    revenue_amount: float
    cost_amount: float
    gross_profit: float = 0.0

    @classmethod
    def from_trade(cls, unit_price: float, quantity: float, moving_avg_cost: float) -> SalesRevenue:
        revenue = round(unit_price * quantity, 2)
        cost = round(moving_avg_cost * quantity, 2)
        return cls(revenue_amount=revenue, cost_amount=cost, gross_profit=round(revenue - cost, 2))