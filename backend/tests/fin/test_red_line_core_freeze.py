"""红线测试 T15-7 - Core Freeze：11 个冻结聚合根不可变、契约稳定。

验证 EITP-FIN-001 的核心冻结红线：
- 11 个 FIN 聚合根均为 frozen dataclass（实例不可变）
- 每个聚合根都有 create 工厂方法
- CORE_FREEZE_VIOLATION 错误码存在
- 审计动作 CORE_FREEZE_VIOLATED / FIN_CORE_FREEZE_VIOLATION 存在
- FINError(CORE_FREEZE_VIOLATION) 可正确构造
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from decimal import Decimal

import pytest

from app.domain.audit.audit_entry import AuditAction
from app.domain.fin.aggregates.ap_voucher_aggregate import APVoucherAggregate
from app.domain.fin.aggregates.ar_voucher_aggregate import ARVoucherAggregate
from app.domain.fin.aggregates.gl_account_aggregate import GLAccountAggregate
from app.domain.fin.aggregates.gl_voucher_aggregate import GLVoucherAggregate
from app.domain.fin.aggregates.invoice_aggregate import InvoiceAggregate
from app.domain.fin.aggregates.payment_aggregate import PaymentAggregate
from app.domain.fin.aggregates.reconciliation_aggregate import ReconciliationAggregate
from app.domain.fin.aggregates.receipt_aggregate import ReceiptAggregate
from app.domain.fin.aggregates.settlement_aggregate import SettlementAggregate
from app.domain.fin.aggregates.treasury_account_aggregate import TreasuryAccountAggregate
from app.domain.fin.aggregates.treasury_transfer_aggregate import TreasuryTransferAggregate
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from tests.fin.conftest import (
    TENANT_ID,
    make_ap_voucher,
    make_ar_voucher,
    make_gl_account,
    make_invoice,
    make_payment,
    make_settlement,
    make_treasury_account,
    make_treasury_transfer,
)

# --------------------------------------------------------------------------- #
# 11 个冻结聚合根
# --------------------------------------------------------------------------- #

FROZEN_AGGREGATES = [
    SettlementAggregate,
    PaymentAggregate,
    ReceiptAggregate,
    InvoiceAggregate,
    ARVoucherAggregate,
    APVoucherAggregate,
    GLVoucherAggregate,
    GLAccountAggregate,
    TreasuryAccountAggregate,
    TreasuryTransferAggregate,
    ReconciliationAggregate,
]

AGGREGATE_NAMES = [
    "SettlementAggregate",
    "PaymentAggregate",
    "ReceiptAggregate",
    "InvoiceAggregate",
    "ARVoucherAggregate",
    "APVoucherAggregate",
    "GLVoucherAggregate",
    "GLAccountAggregate",
    "TreasuryAccountAggregate",
    "TreasuryTransferAggregate",
    "ReconciliationAggregate",
]


class TestCoreFreezeContract:
    """红线 1：11 个冻结聚合根的类契约。"""

    def test_frozen_aggregate_count_is_exactly_11(self) -> None:
        assert len(FROZEN_AGGREGATES) == 11
        assert len(AGGREGATE_NAMES) == 11

    @pytest.mark.parametrize("agg_cls", FROZEN_AGGREGATES, ids=AGGREGATE_NAMES)
    def test_aggregate_is_dataclass(self, agg_cls: type) -> None:
        assert is_dataclass(agg_cls), f"{agg_cls.__name__} 必须是 dataclass"

    @pytest.mark.parametrize("agg_cls", FROZEN_AGGREGATES, ids=AGGREGATE_NAMES)
    def test_aggregate_is_frozen(self, agg_cls: type) -> None:
        params = getattr(agg_cls, "__dataclass_params__", None)
        assert params is not None, f"{agg_cls.__name__} 缺少 __dataclass_params__"
        assert params.frozen, f"{agg_cls.__name__} 必须是 frozen dataclass"

    @pytest.mark.parametrize("agg_cls", FROZEN_AGGREGATES, ids=AGGREGATE_NAMES)
    def test_aggregate_has_create_factory(self, agg_cls: type) -> None:
        assert hasattr(agg_cls, "create"), f"{agg_cls.__name__} 必须有 create 工厂方法"
        assert callable(getattr(agg_cls, "create"))

    @pytest.mark.parametrize("agg_cls", FROZEN_AGGREGATES, ids=AGGREGATE_NAMES)
    def test_aggregate_has_tenant_id_field(self, agg_cls: type) -> None:
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(agg_cls)}
        assert "tenant_id" in field_names, f"{agg_cls.__name__} 必须有 tenant_id 字段"


class TestCoreFreezeImmutability:
    """红线 1：冻结聚合根实例不可变。"""

    def test_settlement_immutable(self) -> None:
        agg = make_settlement()
        with pytest.raises(FrozenInstanceError):
            agg.settlement_no = "HACKED"  # type: ignore[misc]

    def test_payment_immutable(self) -> None:
        agg = make_payment()
        with pytest.raises(FrozenInstanceError):
            agg.payment_no = "HACKED"  # type: ignore[misc]

    def test_invoice_immutable(self) -> None:
        agg = make_invoice()
        with pytest.raises(FrozenInstanceError):
            agg.invoice_no = "HACKED"  # type: ignore[misc]

    def test_ar_voucher_immutable(self) -> None:
        agg = make_ar_voucher()
        with pytest.raises(FrozenInstanceError):
            agg.voucher_no = "HACKED"  # type: ignore[misc]

    def test_ap_voucher_immutable(self) -> None:
        agg = make_ap_voucher()
        with pytest.raises(FrozenInstanceError):
            agg.voucher_no = "HACKED"  # type: ignore[misc]

    def test_gl_account_immutable(self) -> None:
        agg = make_gl_account()
        with pytest.raises(FrozenInstanceError):
            agg.account_code = "HACKED"  # type: ignore[misc]

    def test_treasury_account_immutable(self) -> None:
        agg = make_treasury_account()
        with pytest.raises(FrozenInstanceError):
            agg.account_no = "HACKED"  # type: ignore[misc]

    def test_treasury_transfer_immutable(self) -> None:
        agg = make_treasury_transfer()
        with pytest.raises(FrozenInstanceError):
            agg.transfer_no = "HACKED"  # type: ignore[misc]

    def test_reconciliation_immutable(self) -> None:
        from datetime import date

        from app.domain.fin.aggregates.reconciliation_aggregate import ReconciliationAggregate

        agg = ReconciliationAggregate.create(
            recon_no="RECON-001",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            scope_type="BANK",
            scope_value="BANK-001",
            data_source="BANK_STATEMENT",
            currency="CNY",
            tenant_id=TENANT_ID,
        )
        with pytest.raises(FrozenInstanceError):
            agg.recon_no = "HACKED"  # type: ignore[misc]

    def test_receipt_immutable(self) -> None:
        from app.domain.fin.aggregates.receipt_aggregate import ReceiptAggregate
        from app.domain.fin.value_objects.money import Money

        agg = ReceiptAggregate.create(
            receipt_no="REC-001",
            receipt_amount=Money(Decimal("100.00")),
            receiver_account="BANK-A",
            payer_account="BANK-B",
            bank_ref="REF-001",
            tenant_id=TENANT_ID,
        )
        with pytest.raises(FrozenInstanceError):
            agg.receipt_no = "HACKED"  # type: ignore[misc]

    def test_gl_voucher_immutable(self) -> None:
        from datetime import date

        from app.domain.fin.aggregates.gl_voucher_aggregate import GLVoucherAggregate
        from app.domain.fin.aggregates.gl_voucher_aggregate import GLVoucherLine
        from app.domain.fin.value_objects.money import Money

        line = GLVoucherLine(
            line_no=1,
            account_code="1001",
            debit_amount=Money(Decimal("100.00")),
            credit_amount=Money.zero(),
        )
        agg = GLVoucherAggregate.create(
            voucher_no="GLV-001",
            voucher_date=date(2025, 1, 1),
            summary="测试凭证",
            period="2025-01",
            lines=[line],
            tenant_id=TENANT_ID,
        )
        with pytest.raises(FrozenInstanceError):
            agg.voucher_no = "HACKED"  # type: ignore[misc]


class TestCoreFreezeViolationSignal:
    """红线 1：Core Freeze 违规信号链。"""

    def test_core_freeze_violation_error_code_exists(self) -> None:
        assert hasattr(FINErrorCode, "CORE_FREEZE_VIOLATION")

    def test_core_freeze_violation_error_code_value(self) -> None:
        assert FINErrorCode.CORE_FREEZE_VIOLATION.value == "EITP_FIN_CORE_FREEZE_VIOLATION"

    def test_core_freeze_violation_has_eitp_fin_prefix(self) -> None:
        assert FINErrorCode.CORE_FREEZE_VIOLATION.value.startswith("EITP_FIN_")

    def test_audit_action_core_freeze_violated_exists(self) -> None:
        assert hasattr(AuditAction, "CORE_FREEZE_VIOLATED")
        assert AuditAction.CORE_FREEZE_VIOLATED.value == "core_freeze_violated"

    def test_audit_action_fin_core_freeze_violation_exists(self) -> None:
        assert hasattr(AuditAction, "FIN_CORE_FREEZE_VIOLATION")
        assert AuditAction.FIN_CORE_FREEZE_VIOLATION.value == "fin_core_freeze_violation"

    def test_fin_error_with_core_freeze_violation(self) -> None:
        err = FINError(
            FINErrorCode.CORE_FREEZE_VIOLATION,
            "attempted to modify frozen aggregate",
        )
        assert err.code is FINErrorCode.CORE_FREEZE_VIOLATION
        assert err.message == "attempted to modify frozen aggregate"
        assert err.details == {}

    def test_fin_error_with_core_freeze_violation_and_details(self) -> None:
        err = FINError(
            FINErrorCode.CORE_FREEZE_VIOLATION,
            "attempted to modify frozen aggregate",
            details={"aggregate": "SettlementAggregate", "field": "settlement_no"},
        )
        assert err.details["aggregate"] == "SettlementAggregate"
        assert err.details["field"] == "settlement_no"

    def test_core_freeze_violation_is_distinct_from_internal_error(self) -> None:
        assert FINErrorCode.CORE_FREEZE_VIOLATION != FINErrorCode.INTERNAL_ERROR
        assert (
            FINErrorCode.CORE_FREEZE_VIOLATION.value
            != FINErrorCode.INTERNAL_ERROR.value
        )