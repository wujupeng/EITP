"""SAL 销售退货值对象 - SalesReturnStatus/QcResult/Disposition。"""

from __future__ import annotations

from enum import Enum


class SalesReturnStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    RECEIVING = "receiving"
    QC_PENDING = "qc_pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QcResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL_PASSED = "partial_passed"
    QUARANTINED = "quarantined"


class Disposition(str, Enum):
    RESTOCK = "restock"
    QUARANTINE = "quarantine"
    SCRAP = "scrap"