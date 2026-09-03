"""FIN 财务域枚举完整性单元测试 - 校验所有枚举值与设计规格一致。

覆盖 SettlementType/Status、PaymentStatus、ReceiptStatus、InvoiceStatus/Type、
PaymentMethod、VoucherType/Status、GLAccountCategory、BalanceDirection、
TreasuryAccountType、TransferStatus、ReconciliationStatus、DifferenceType、
HandleStatus、CollectionStage/TaskStatus、AgingBucket 全部枚举。
"""

from __future__ import annotations

from app.domain.fin.value_objects.enums import (
    AgingBucket,
    BalanceDirection,
    CollectionStage,
    CollectionTaskStatus,
    DifferenceType,
    GLAccountCategory,
    HandleStatus,
    InvoiceStatus,
    InvoiceType,
    PaymentMethod,
    PaymentStatus,
    ReceiptStatus,
    ReconciliationStatus,
    SettlementStatus,
    SettlementType,
    TransferStatus,
    TreasuryAccountType,
    VoucherStatus,
    VoucherType,
)


def _values(enum_cls: type) -> set[str]:
    return {e.value for e in enum_cls}


class SettlementTypeTest:
    def test_values(self) -> None:
        assert _values(SettlementType) == {"PURCHASE", "SALES", "CROSS_TENANT"}


class SettlementStatusTest:
    def test_values(self) -> None:
        assert _values(SettlementStatus) == {
            "DRAFT",
            "CONFIRMED",
            "SETTLED",
            "CLOSED",
            "CANCELLED",
        }


class PaymentStatusTest:
    def test_values(self) -> None:
        assert _values(PaymentStatus) == {
            "DRAFT",
            "PENDING_APPROVAL",
            "APPROVED",
            "EXECUTING",
            "SUCCESS",
            "FAILED",
            "CANCELLED",
        }


class ReceiptStatusTest:
    def test_values(self) -> None:
        assert _values(ReceiptStatus) == {
            "PENDING_CONFIRM",
            "CONFIRMED",
            "WRITE_OFF",
            "CANCELLED",
        }


class InvoiceStatusTest:
    def test_values(self) -> None:
        assert _values(InvoiceStatus) == {
            "DRAFT",
            "ISSUED",
            "MATCHED",
            "VERIFIED",
            "ARCHIVED",
            "VOID",
        }


class InvoiceTypeTest:
    def test_values(self) -> None:
        assert _values(InvoiceType) == {
            "VAT_SPECIAL",
            "VAT_NORMAL",
            "ELECTRONIC",
            "RED",
        }


class PaymentMethodTest:
    def test_values(self) -> None:
        assert _values(PaymentMethod) == {
            "BANK_TRANSFER",
            "ACCEPTANCE",
            "CASH",
            "INTERNAL_TRANSFER",
        }


class VoucherTypeTest:
    def test_values(self) -> None:
        assert _values(VoucherType) == {"AR", "AP"}


class VoucherStatusTest:
    def test_values(self) -> None:
        assert _values(VoucherStatus) == {"OPEN", "PARTIAL", "SETTLED", "RED"}


class GLAccountCategoryTest:
    def test_values(self) -> None:
        assert _values(GLAccountCategory) == {
            "ASSET",
            "LIABILITY",
            "EQUITY",
            "REVENUE",
            "COST",
            "EXPENSE",
        }


class BalanceDirectionTest:
    def test_values(self) -> None:
        assert _values(BalanceDirection) == {"DEBIT", "CREDIT"}


class TreasuryAccountTypeTest:
    def test_values(self) -> None:
        assert _values(TreasuryAccountType) == {"BANK", "INTERNAL"}


class TransferStatusTest:
    def test_values(self) -> None:
        assert _values(TransferStatus) == {
            "PENDING_APPROVAL",
            "APPROVED",
            "EXECUTING",
            "SUCCESS",
            "FAILED",
            "CANCELLED",
        }


class ReconciliationStatusTest:
    def test_values(self) -> None:
        assert _values(ReconciliationStatus) == {
            "CREATED",
            "MATCHING",
            "MATCHED",
            "DIFF_HANDLING",
            "COMPLETED",
            "FAILED",
        }


class DifferenceTypeTest:
    def test_values(self) -> None:
        assert _values(DifferenceType) == {
            "AMOUNT_DIFF",
            "TIME_DIFF",
            "MISSING_DOC",
            "DUPLICATE",
        }


class HandleStatusTest:
    def test_values(self) -> None:
        assert _values(HandleStatus) == {
            "PENDING",
            "WRITE_OFF",
            "HANG",
            "INVESTIGATE",
        }


class CollectionStageTest:
    def test_values(self) -> None:
        assert _values(CollectionStage) == {"REMINDER", "URGENT", "LEGAL"}


class CollectionTaskStatusTest:
    def test_values(self) -> None:
        assert _values(CollectionTaskStatus) == {
            "PENDING",
            "IN_PROGRESS",
            "RESOLVED",
            "ESCALATED",
        }


class AgingBucketTest:
    def test_values(self) -> None:
        assert _values(AgingBucket) == {
            "B_0_30",
            "B_31_60",
            "B_61_90",
            "B_91_180",
            "B_180_PLUS",
        }


class EnumStrMixinTest:
    """所有 FIN 枚举继承 str，确保 value == 枚举成员本身。"""

    def test_all_enums_are_str_enum(self) -> None:
        enums = [
            SettlementType,
            SettlementStatus,
            PaymentStatus,
            ReceiptStatus,
            InvoiceStatus,
            InvoiceType,
            PaymentMethod,
            VoucherType,
            VoucherStatus,
            GLAccountCategory,
            BalanceDirection,
            TreasuryAccountType,
            TransferStatus,
            ReconciliationStatus,
            DifferenceType,
            HandleStatus,
            CollectionStage,
            CollectionTaskStatus,
            AgingBucket,
        ]
        for enum_cls in enums:
            for member in enum_cls:
                assert isinstance(member, str)
                assert member.value == member