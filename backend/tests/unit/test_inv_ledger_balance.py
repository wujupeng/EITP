"""EITP-INV-001 库存账本聚合根与库存余额聚合根单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.inventory.aggregates.inventory_balance_aggregate import (
    InventoryBalanceAggregate,
)
from app.domain.inventory.aggregates.inventory_ledger_aggregate import (
    InventoryLedgerAggregate,
)
from app.domain.inventory.value_objects.shared import Direction, TransactionType
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


@pytest.fixture
def tenant_id() -> uuid4:
    return uuid4()


@pytest.fixture
def sku_id() -> uuid4:
    return uuid4()


@pytest.fixture
def warehouse_id() -> uuid4:
    return uuid4()


@pytest.fixture
def operated_by() -> uuid4:
    return uuid4()


def _make_ledger(
    *,
    transaction_id: uuid4 | None = None,
    tenant_id: uuid4 | None = None,
    sku_id: uuid4 | None = None,
    warehouse_id: uuid4 | None = None,
    transaction_type: TransactionType | None = TransactionType.PURCHASE_RECEIPT,
    quantity_before: float = 0.0,
    quantity_change: float = 100.0,
    quantity_after: float = 100.0,
    operated_by: uuid4 | None = None,
) -> InventoryLedgerAggregate:
    return InventoryLedgerAggregate(
        id=EntityId.generate(),
        transaction_id=transaction_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        sku_id=sku_id or uuid4(),
        warehouse_id=warehouse_id or uuid4(),
        transaction_type=transaction_type,
        quantity_before=quantity_before,
        quantity_change=quantity_change,
        quantity_after=quantity_after,
        operated_by=operated_by or uuid4(),
    )


class InventoryLedgerAggregateTest:
    def test_create_with_all_required_fields(
        self, tenant_id: uuid4, sku_id: uuid4, warehouse_id: uuid4, operated_by: uuid4
    ) -> None:
        tx_id = uuid4()
        ledger = InventoryLedgerAggregate(
            id=EntityId.generate(),
            transaction_id=tx_id,
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            transaction_type=TransactionType.PURCHASE_RECEIPT,
            quantity_before=0.0,
            quantity_change=100.0,
            quantity_after=100.0,
            operated_by=operated_by,
            idempotency_key="idem-1",
            unit_cost=10.0,
            total_cost=1000.0,
        )
        assert ledger.transaction_id == tx_id
        assert ledger.tenant_id == tenant_id
        assert ledger.sku_id == sku_id
        assert ledger.warehouse_id == warehouse_id
        assert ledger.transaction_type == TransactionType.PURCHASE_RECEIPT
        assert ledger.direction == Direction.INBOUND
        assert ledger.quantity_before == 0.0
        assert ledger.quantity_change == 100.0
        assert ledger.quantity_after == 100.0
        assert ledger.operated_by == operated_by
        assert ledger.idempotency_key == "idem-1"
        assert ledger.unit_cost == 10.0
        assert ledger.operated_at is not None

    def test_missing_transaction_id_rejected(
        self, tenant_id: uuid4, sku_id: uuid4, warehouse_id: uuid4, operated_by: uuid4
    ) -> None:
        with pytest.raises(INVError) as exc:
            InventoryLedgerAggregate(
                id=EntityId.generate(),
                transaction_id=None,
                tenant_id=tenant_id,
                sku_id=sku_id,
                warehouse_id=warehouse_id,
                transaction_type=TransactionType.PURCHASE_RECEIPT,
                quantity_before=0.0,
                quantity_change=10.0,
                quantity_after=10.0,
                operated_by=operated_by,
            )
        assert exc.value.code == INVErrorCode.LEDGER_FIELD_REQUIRED

    def test_missing_operated_by_rejected(
        self, tenant_id: uuid4, sku_id: uuid4, warehouse_id: uuid4
    ) -> None:
        with pytest.raises(INVError) as exc:
            InventoryLedgerAggregate(
                id=EntityId.generate(),
                transaction_id=uuid4(),
                tenant_id=tenant_id,
                sku_id=sku_id,
                warehouse_id=warehouse_id,
                transaction_type=TransactionType.PURCHASE_RECEIPT,
                quantity_before=0.0,
                quantity_change=10.0,
                quantity_after=10.0,
                operated_by=None,
            )
        assert exc.value.code == INVErrorCode.LEDGER_FIELD_REQUIRED

    def test_missing_multiple_fields_rejected(self) -> None:
        with pytest.raises(INVError) as exc:
            InventoryLedgerAggregate(
                id=EntityId.generate(),
                transaction_id=None,
                tenant_id=None,
                sku_id=None,
                warehouse_id=None,
                transaction_type=None,
                quantity_before=0.0,
                quantity_change=10.0,
                quantity_after=10.0,
                operated_by=None,
            )
        assert exc.value.code == INVErrorCode.LEDGER_FIELD_REQUIRED
        assert "transaction_id" in exc.value.message
        assert "operated_by" in exc.value.message

    def test_quantity_inconsistency_rejected(
        self, tenant_id: uuid4, sku_id: uuid4, warehouse_id: uuid4, operated_by: uuid4
    ) -> None:
        with pytest.raises(INVError) as exc:
            InventoryLedgerAggregate(
                id=EntityId.generate(),
                transaction_id=uuid4(),
                tenant_id=tenant_id,
                sku_id=sku_id,
                warehouse_id=warehouse_id,
                transaction_type=TransactionType.PURCHASE_RECEIPT,
                quantity_before=0.0,
                quantity_change=100.0,
                quantity_after=99.0,
                operated_by=operated_by,
            )
        assert exc.value.code == INVErrorCode.LEDGER_FIELD_REQUIRED

    def test_quantity_consistency_within_tolerance(self) -> None:
        ledger = _make_ledger(
            quantity_before=0.0,
            quantity_change=100.0,
            quantity_after=100.00005,
        )
        assert ledger.quantity_after == pytest.approx(100.00005)

    def test_all_optional_properties_access(self) -> None:
        correlation_id = "corr-abc"
        document_id = uuid4()
        organization_id = uuid4()
        site_id = uuid4()
        location_id = uuid4()
        ledger = InventoryLedgerAggregate(
            id=EntityId.generate(),
            transaction_id=uuid4(),
            tenant_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            transaction_type=TransactionType.SALES_ISSUE,
            quantity_before=100.0,
            quantity_change=-30.0,
            quantity_after=70.0,
            operated_by=uuid4(),
            correlation_id=correlation_id,
            document_id=document_id,
            document_type="sales_order",
            idempotency_key="idem-x",
            organization_id=organization_id,
            site_id=site_id,
            location_id=location_id,
            unit_cost=5.0,
            total_cost=150.0,
            reason="测试原因",
        )
        assert ledger.correlation_id == correlation_id
        assert ledger.document_id == document_id
        assert ledger.document_type == "sales_order"
        assert ledger.idempotency_key == "idem-x"
        assert ledger.organization_id == organization_id
        assert ledger.site_id == site_id
        assert ledger.location_id == location_id
        assert ledger.unit_cost == 5.0
        assert ledger.total_cost == 150.0
        assert ledger.reason == "测试原因"
        assert ledger.direction == Direction.OUTBOUND


def _make_balance(
    *,
    tenant_id: uuid4 | None = None,
    sku_id: uuid4 | None = None,
    warehouse_id: uuid4 | None = None,
    on_hand: float = 0.0,
    reserved: float = 0.0,
    in_transit: float = 0.0,
    inspection: float = 0.0,
    blocked: float = 0.0,
) -> InventoryBalanceAggregate:
    return InventoryBalanceAggregate(
        id=EntityId.generate(),
        tenant_id=tenant_id or uuid4(),
        sku_id=sku_id or uuid4(),
        warehouse_id=warehouse_id or uuid4(),
        on_hand=on_hand,
        reserved=reserved,
        in_transit=in_transit,
        inspection=inspection,
        blocked=blocked,
    )


class InventoryBalanceAggregateTest:
    def test_create_with_six_state_quantities(self) -> None:
        balance = _make_balance(
            on_hand=100.0, reserved=30.0, in_transit=20.0, inspection=10.0, blocked=5.0
        )
        assert balance.on_hand == 100.0
        assert balance.reserved == 30.0
        assert balance.in_transit == 20.0
        assert balance.inspection == 10.0
        assert balance.blocked == 5.0

    def test_available_is_computed_from_on_hand_minus_reserved(self) -> None:
        balance = _make_balance(on_hand=100.0, reserved=30.0)
        assert balance.available == 70.0
        assert balance.recompute_available() == 70.0

    def test_available_updates_when_reserved_changes(self) -> None:
        balance = _make_balance(on_hand=100.0, reserved=0.0)
        assert balance.available == 100.0
        balance.add_reservation(40.0)
        assert balance.reserved == 40.0
        assert balance.available == 60.0

    def test_apply_transaction_purchase_receipt_increases_on_hand(self) -> None:
        balance = _make_balance(on_hand=0.0)
        balance.apply_transaction(TransactionType.PURCHASE_RECEIPT, 100.0, uuid4())
        assert balance.on_hand == 100.0
        assert balance.available == 100.0

    def test_apply_transaction_sales_issue_decreases_on_hand(self) -> None:
        balance = _make_balance(on_hand=100.0)
        balance.apply_transaction(TransactionType.SALES_ISSUE, 30.0, uuid4())
        assert balance.on_hand == 70.0

    def test_apply_transaction_transfer_out_moves_to_in_transit(self) -> None:
        balance = _make_balance(on_hand=100.0)
        balance.apply_transaction(TransactionType.TRANSFER_OUT, 40.0, uuid4())
        assert balance.on_hand == 60.0
        assert balance.in_transit == 40.0

    def test_apply_transaction_transfer_in_moves_from_in_transit(self) -> None:
        balance = _make_balance(on_hand=60.0, in_transit=40.0)
        balance.apply_transaction(TransactionType.TRANSFER_IN, 40.0, uuid4())
        assert balance.in_transit == 0.0
        assert balance.on_hand == 100.0

    def test_apply_transaction_adjustment_in(self) -> None:
        balance = _make_balance(on_hand=50.0)
        balance.apply_transaction(TransactionType.ADJUSTMENT_IN, 5.0, uuid4())
        assert balance.on_hand == 55.0

    def test_apply_transaction_adjustment_out(self) -> None:
        balance = _make_balance(on_hand=50.0)
        balance.apply_transaction(TransactionType.ADJUSTMENT_OUT, 5.0, uuid4())
        assert balance.on_hand == 45.0

    def test_apply_transaction_return_in(self) -> None:
        balance = _make_balance(on_hand=50.0)
        balance.apply_transaction(TransactionType.RETURN_IN, 10.0, uuid4())
        assert balance.on_hand == 60.0

    def test_apply_transaction_return_out(self) -> None:
        balance = _make_balance(on_hand=50.0)
        balance.apply_transaction(TransactionType.RETURN_OUT, 10.0, uuid4())
        assert balance.on_hand == 40.0

    def test_apply_transaction_inspect_pass_moves_inspection_to_on_hand(self) -> None:
        balance = _make_balance(on_hand=0.0, inspection=20.0)
        balance.apply_transaction(TransactionType.INSPECT_PASS, 20.0, uuid4())
        assert balance.inspection == 0.0
        assert balance.on_hand == 20.0

    def test_apply_transaction_inspect_fail_reduces_inspection(self) -> None:
        balance = _make_balance(inspection=20.0)
        balance.apply_transaction(TransactionType.INSPECT_FAIL, 20.0, uuid4())
        assert balance.inspection == 0.0
        assert balance.on_hand == 0.0

    def test_apply_transaction_block_moves_on_hand_to_blocked(self) -> None:
        balance = _make_balance(on_hand=80.0)
        balance.apply_transaction(TransactionType.BLOCK, 30.0, uuid4())
        assert balance.on_hand == 50.0
        assert balance.blocked == 30.0

    def test_apply_transaction_unblock_moves_blocked_to_on_hand(self) -> None:
        balance = _make_balance(on_hand=50.0, blocked=30.0)
        balance.apply_transaction(TransactionType.UNBLOCK, 30.0, uuid4())
        assert balance.blocked == 0.0
        assert balance.on_hand == 80.0

    def test_apply_transaction_rejects_non_positive_quantity(self) -> None:
        balance = _make_balance(on_hand=100.0)
        with pytest.raises(INVError) as exc:
            balance.apply_transaction(TransactionType.PURCHASE_RECEIPT, 0.0, uuid4())
        assert exc.value.code == INVErrorCode.LEDGER_FIELD_REQUIRED

    def test_apply_transaction_updates_unit_cost_and_last_ledger(self) -> None:
        balance = _make_balance(on_hand=0.0)
        ledger_id = uuid4()
        balance.apply_transaction(
            TransactionType.PURCHASE_RECEIPT, 100.0, ledger_id, unit_cost=12.5
        )
        assert balance.unit_cost == 12.5
        assert balance.last_ledger_id == ledger_id

    def test_add_reservation_rejects_when_insufficient_available(self) -> None:
        balance = _make_balance(on_hand=50.0, reserved=30.0)
        assert balance.available == 20.0
        with pytest.raises(INVError) as exc:
            balance.add_reservation(30.0)
        assert exc.value.code == INVErrorCode.INSUFFICIENT_AVAILABLE
        assert balance.reserved == 30.0

    def test_add_reservation_succeeds_when_available_sufficient(self) -> None:
        balance = _make_balance(on_hand=100.0, reserved=20.0)
        balance.add_reservation(50.0)
        assert balance.reserved == 70.0
        assert balance.available == 30.0

    def test_release_reservation_reduces_reserved(self) -> None:
        balance = _make_balance(on_hand=100.0, reserved=50.0)
        balance.release_reservation(20.0)
        assert balance.reserved == 30.0
        assert balance.available == 70.0

    def test_release_reservation_clamps_to_zero(self) -> None:
        balance = _make_balance(on_hand=100.0, reserved=10.0)
        balance.release_reservation(100.0)
        assert balance.reserved == 0.0

    def test_consume_reservation_reduces_reserved(self) -> None:
        balance = _make_balance(on_hand=100.0, reserved=50.0)
        balance.consume_reservation(20.0)
        assert balance.reserved == 30.0

    def test_golden_path_receipt_reserve_issue(self) -> None:
        balance = _make_balance(on_hand=0.0)
        balance.apply_transaction(TransactionType.PURCHASE_RECEIPT, 100.0, uuid4())
        assert balance.on_hand == 100.0
        balance.add_reservation(30.0)
        assert balance.reserved == 30.0
        assert balance.available == 70.0
        balance.consume_reservation(30.0)
        assert balance.reserved == 0.0
        balance.apply_transaction(TransactionType.SALES_ISSUE, 30.0, uuid4())
        assert balance.on_hand == 70.0
        assert balance.available == 70.0

    def test_properties_access(self) -> None:
        tenant_id = uuid4()
        sku_id = uuid4()
        warehouse_id = uuid4()
        location_id = uuid4()
        balance = InventoryBalanceAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            batch_no="BATCH-01",
            unit_cost=8.0,
        )
        assert balance.tenant_id == tenant_id
        assert balance.sku_id == sku_id
        assert balance.warehouse_id == warehouse_id
        assert balance.location_id == location_id
        assert balance.batch_no == "BATCH-01"
        assert balance.unit_cost == 8.0

    def test_add_reservation_non_positive_quantity_is_noop(self) -> None:
        balance = _make_balance(on_hand=100.0, reserved=20.0)
        balance.add_reservation(0.0)
        assert balance.reserved == 20.0

    def test_release_reservation_non_positive_quantity_is_noop(self) -> None:
        balance = _make_balance(on_hand=100.0, reserved=20.0)
        balance.release_reservation(0.0)
        assert balance.reserved == 20.0

    def test_consume_reservation_non_positive_quantity_is_noop(self) -> None:
        balance = _make_balance(on_hand=100.0, reserved=20.0)
        balance.consume_reservation(0.0)
        assert balance.reserved == 20.0