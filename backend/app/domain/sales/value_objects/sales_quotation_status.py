"""SAL 销售报价状态枚举。"""

from __future__ import annotations

from enum import Enum


class SalesQuotationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"