"""FIN 财务域状态枚举与业务类型枚举。"""

from __future__ import annotations

from enum import Enum


class SettlementType(str, Enum):
    PURCHASE = "PURCHASE"
    SALES = "SALES"
    CROSS_TENANT = "CROSS_TENANT"


class SettlementStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SETTLED = "SETTLED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ReceiptStatus(str, Enum):
    PENDING_CONFIRM = "PENDING_CONFIRM"
    CONFIRMED = "CONFIRMED"
    WRITE_OFF = "WRITE_OFF"
    CANCELLED = "CANCELLED"


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    MATCHED = "MATCHED"
    VERIFIED = "VERIFIED"
    ARCHIVED = "ARCHIVED"
    VOID = "VOID"


class InvoiceType(str, Enum):
    VAT_SPECIAL = "VAT_SPECIAL"
    VAT_NORMAL = "VAT_NORMAL"
    ELECTRONIC = "ELECTRONIC"
    RED = "RED"


class PaymentMethod(str, Enum):
    BANK_TRANSFER = "BANK_TRANSFER"
    ACCEPTANCE = "ACCEPTANCE"
    CASH = "CASH"
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"


class VoucherType(str, Enum):
    AR = "AR"
    AP = "AP"


class VoucherStatus(str, Enum):
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    SETTLED = "SETTLED"
    RED = "RED"


class GLAccountCategory(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    COST = "COST"
    EXPENSE = "EXPENSE"


class BalanceDirection(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class TreasuryAccountType(str, Enum):
    BANK = "BANK"
    INTERNAL = "INTERNAL"


class TransferStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ReconciliationStatus(str, Enum):
    CREATED = "CREATED"
    MATCHING = "MATCHING"
    MATCHED = "MATCHED"
    DIFF_HANDLING = "DIFF_HANDLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DifferenceType(str, Enum):
    AMOUNT_DIFF = "AMOUNT_DIFF"
    TIME_DIFF = "TIME_DIFF"
    MISSING_DOC = "MISSING_DOC"
    DUPLICATE = "DUPLICATE"


class HandleStatus(str, Enum):
    PENDING = "PENDING"
    WRITE_OFF = "WRITE_OFF"
    HANG = "HANG"
    INVESTIGATE = "INVESTIGATE"


class CollectionStage(str, Enum):
    REMINDER = "REMINDER"
    URGENT = "URGENT"
    LEGAL = "LEGAL"


class CollectionTaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class AgingBucket(str, Enum):
    B_0_30 = "B_0_30"
    B_31_60 = "B_31_60"
    B_61_90 = "B_61_90"
    B_91_180 = "B_91_180"
    B_180_PLUS = "B_180_PLUS"