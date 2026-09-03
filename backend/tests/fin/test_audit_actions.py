"""红线测试 T15-13 - 审计动作：FIN 相关 AuditAction 完整性与 AuditEntry 不可变。

验证 EITP-FIN-001 的审计红线：
- 28 个 FIN 相关 AuditAction 值存在且字符串值正确
- AuditEntry.create 工厂方法正确构建条目
- AuditEntry 是 frozen dataclass（不可篡改）
- 审计条目包含完整字段（tenant_id, user_id, action, entity_type, entity_id, occurred_at）
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.domain.audit.audit_entry import AuditAction, AuditEntry
from tests.fin.conftest import TENANT_ID, USER_ID

# --------------------------------------------------------------------------- #
# 28 个 FIN 相关 AuditAction
# --------------------------------------------------------------------------- #

FIN_AUDIT_ACTIONS = [
    (AuditAction.SETTLEMENT_CREATED, "settlement_created"),
    (AuditAction.SETTLEMENT_CONFIRMED, "settlement_confirmed"),
    (AuditAction.SETTLEMENT_SETTLED, "settlement_settled"),
    (AuditAction.SETTLEMENT_CANCELLED, "settlement_cancelled"),
    (AuditAction.PAYMENT_REQUESTED, "payment_requested"),
    (AuditAction.PAYMENT_APPROVED, "payment_approved"),
    (AuditAction.PAYMENT_EXECUTING, "payment_executing"),
    (AuditAction.PAYMENT_SUCCESS, "payment_success"),
    (AuditAction.PAYMENT_FAILED, "payment_failed"),
    (AuditAction.RECEIPT_CONFIRMED, "receipt_confirmed"),
    (AuditAction.RECEIPT_WRITE_OFF, "receipt_write_off"),
    (AuditAction.INVOICE_ISSUED, "invoice_issued"),
    (AuditAction.INVOICE_MATCHED, "invoice_matched"),
    (AuditAction.INVOICE_VERIFIED, "invoice_verified"),
    (AuditAction.INVOICE_ARCHIVED, "invoice_archived"),
    (AuditAction.INVOICE_VOID, "invoice_void"),
    (AuditAction.RECON_BATCH_CREATED, "recon_batch_created"),
    (AuditAction.RECON_DIFFERENCE_HANDLED, "recon_difference_handled"),
    (AuditAction.AR_VOUCHER_GENERATED, "ar_voucher_generated"),
    (AuditAction.AP_VOUCHER_GENERATED, "ap_voucher_generated"),
    (AuditAction.GL_VOUCHER_POSTED, "gl_voucher_posted"),
    (AuditAction.GL_PERIOD_CLOSED, "gl_period_closed"),
    (AuditAction.GL_RED_VOUCHER_CREATED, "gl_red_voucher_created"),
    (AuditAction.TREASURY_TRANSFER_EXECUTED, "treasury_transfer_executed"),
    (AuditAction.TREASURY_FREEZED, "treasury_freezed"),
    (AuditAction.TREASURY_UNFREEZED, "treasury_unfrozen"),
    (AuditAction.COLLECTION_TASK_GENERATED, "collection_task_generated"),
    (AuditAction.FIN_CORE_FREEZE_VIOLATION, "fin_core_freeze_violation"),
]


class TestFinAuditActionExists:
    """红线 6：28 个 FIN 相关 AuditAction 存在。"""

    def test_fin_audit_action_count_is_28(self) -> None:
        assert len(FIN_AUDIT_ACTIONS) == 28

    @pytest.mark.parametrize(
        "action,expected_value",
        FIN_AUDIT_ACTIONS,
        ids=[a.name for a, _ in FIN_AUDIT_ACTIONS],
    )
    def test_action_value(self, action: AuditAction, expected_value: str) -> None:
        assert action.value == expected_value

    @pytest.mark.parametrize(
        "action,expected_value",
        FIN_AUDIT_ACTIONS,
        ids=[a.name for a, _ in FIN_AUDIT_ACTIONS],
    )
    def test_action_is_enum_member(self, action: AuditAction, expected_value: str) -> None:
        assert isinstance(action, AuditAction)

    def test_all_values_are_unique(self) -> None:
        values = [a.value for a, _ in FIN_AUDIT_ACTIONS]
        assert len(values) == len(set(values)), "AuditAction 值有重复"

    def test_all_names_are_unique(self) -> None:
        names = [a.name for a, _ in FIN_AUDIT_ACTIONS]
        assert len(names) == len(set(names)), "AuditAction 名称有重复"


class TestFinAuditActionCategories:
    """红线 6：FIN AuditAction 覆盖所有业务领域。"""

    def test_settlement_actions_exist(self) -> None:
        assert hasattr(AuditAction, "SETTLEMENT_CREATED")
        assert hasattr(AuditAction, "SETTLEMENT_CONFIRMED")
        assert hasattr(AuditAction, "SETTLEMENT_SETTLED")
        assert hasattr(AuditAction, "SETTLEMENT_CANCELLED")

    def test_payment_actions_exist(self) -> None:
        assert hasattr(AuditAction, "PAYMENT_REQUESTED")
        assert hasattr(AuditAction, "PAYMENT_APPROVED")
        assert hasattr(AuditAction, "PAYMENT_EXECUTING")
        assert hasattr(AuditAction, "PAYMENT_SUCCESS")
        assert hasattr(AuditAction, "PAYMENT_FAILED")

    def test_receipt_actions_exist(self) -> None:
        assert hasattr(AuditAction, "RECEIPT_CONFIRMED")
        assert hasattr(AuditAction, "RECEIPT_WRITE_OFF")

    def test_invoice_actions_exist(self) -> None:
        assert hasattr(AuditAction, "INVOICE_ISSUED")
        assert hasattr(AuditAction, "INVOICE_MATCHED")
        assert hasattr(AuditAction, "INVOICE_VERIFIED")
        assert hasattr(AuditAction, "INVOICE_ARCHIVED")
        assert hasattr(AuditAction, "INVOICE_VOID")

    def test_recon_actions_exist(self) -> None:
        assert hasattr(AuditAction, "RECON_BATCH_CREATED")
        assert hasattr(AuditAction, "RECON_DIFFERENCE_HANDLED")

    def test_voucher_actions_exist(self) -> None:
        assert hasattr(AuditAction, "AR_VOUCHER_GENERATED")
        assert hasattr(AuditAction, "AP_VOUCHER_GENERATED")

    def test_gl_actions_exist(self) -> None:
        assert hasattr(AuditAction, "GL_VOUCHER_POSTED")
        assert hasattr(AuditAction, "GL_PERIOD_CLOSED")
        assert hasattr(AuditAction, "GL_RED_VOUCHER_CREATED")

    def test_treasury_actions_exist(self) -> None:
        assert hasattr(AuditAction, "TREASURY_TRANSFER_EXECUTED")
        assert hasattr(AuditAction, "TREASURY_FREEZED")
        assert hasattr(AuditAction, "TREASURY_UNFREEZED")

    def test_collection_actions_exist(self) -> None:
        assert hasattr(AuditAction, "COLLECTION_TASK_GENERATED")

    def test_core_freeze_violation_action_exists(self) -> None:
        assert hasattr(AuditAction, "FIN_CORE_FREEZE_VIOLATION")
        assert AuditAction.FIN_CORE_FREEZE_VIOLATION.value == "fin_core_freeze_violation"


class TestAuditEntryImmutability:
    """红线 6：AuditEntry 不可篡改。"""

    def test_audit_entry_is_dataclass(self) -> None:
        assert is_dataclass(AuditEntry)

    def test_audit_entry_is_frozen(self) -> None:
        params = getattr(AuditEntry, "__dataclass_params__", None)
        assert params is not None
        assert params.frozen

    def test_audit_entry_instance_immutable(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-001",
        )
        with pytest.raises(FrozenInstanceError):
            entry.entity_id = "HACKED"  # type: ignore[misc]

    def test_audit_entry_action_immutable(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.PAYMENT_SUCCESS,
            entity_type="Payment",
            entity_id="PAY-001",
        )
        with pytest.raises(FrozenInstanceError):
            entry.action = AuditAction.PAYMENT_FAILED  # type: ignore[misc]


class TestAuditEntryCreate:
    """红线 6：AuditEntry.create 工厂方法。"""

    def test_create_populates_id(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-001",
        )
        assert isinstance(entry.id, UUID)
        assert entry.id is not None

    def test_create_populates_tenant_id(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-001",
        )
        assert entry.tenant_id == TENANT_ID

    def test_create_populates_user_id(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-001",
        )
        assert entry.user_id == USER_ID

    def test_create_populates_action(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.PAYMENT_APPROVED,
            entity_type="Payment",
            entity_id="PAY-001",
        )
        assert entry.action == AuditAction.PAYMENT_APPROVED

    def test_create_populates_entity_fields(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.INVOICE_ISSUED,
            entity_type="Invoice",
            entity_id="INV-001",
        )
        assert entry.entity_type == "Invoice"
        assert entry.entity_id == "INV-001"

    def test_create_populates_occurred_at(self) -> None:
        before = datetime.now(timezone.utc)
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-001",
        )
        after = datetime.now(timezone.utc)
        assert before <= entry.occurred_at <= after

    def test_create_with_old_and_new_value(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_SETTLED,
            entity_type="Settlement",
            entity_id="ST-001",
            old_value={"status": "CONFIRMED"},
            new_value={"status": "SETTLED"},
        )
        assert entry.old_value == {"status": "CONFIRMED"}
        assert entry.new_value == {"status": "SETTLED"}

    def test_create_with_ip_address(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.PAYMENT_SUCCESS,
            entity_type="Payment",
            entity_id="PAY-001",
            ip_address="192.168.1.100",
        )
        assert entry.ip_address == "192.168.1.100"

    def test_create_defaults_old_new_value_to_none(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-001",
        )
        assert entry.old_value is None
        assert entry.new_value is None

    def test_create_defaults_ip_address_to_none(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-001",
        )
        assert entry.ip_address is None

    def test_create_with_none_user_id(self) -> None:
        entry = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=None,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-001",
        )
        assert entry.user_id is None

    def test_each_create_generates_unique_id(self) -> None:
        entry1 = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-001",
        )
        entry2 = AuditEntry.create(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            action=AuditAction.SETTLEMENT_CREATED,
            entity_type="Settlement",
            entity_id="ST-002",
        )
        assert entry1.id != entry2.id