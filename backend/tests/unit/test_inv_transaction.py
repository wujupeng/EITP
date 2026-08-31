"""EITP-INV-001 库存事务聚合根与事务方向值对象单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.inventory.aggregates.inventory_transaction_aggregate import (
    InventoryTransactionAggregate,
)
from app.domain.inventory.value_objects.shared import (
    Direction,
    Ownership,
    TransactionStatus,
    TransactionType,
    direction_of,
)
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


def _make_transaction(
    *,
    tenant_id: uuid4 | None = None,
    sku_id: uuid4 | None = None,
    warehouse_id: uuid4 | None = None,
    transaction_type: TransactionType = TransactionType.PURCHASE_RECEIPT,
    quantity: float = 100.0,
    idempotency_key: str = "idem-key-1",
    status: TransactionStatus = TransactionStatus.PENDING,
) -> InventoryTransactionAggregate:
    return InventoryTransactionAggregate(
        id=EntityId.generate(),
        tenant_id=tenant_id or uuid4(),
        sku_id=sku_id or uuid4(),
        warehouse_id=warehouse_id or uuid4(),
        transaction_type=transaction_type,
        quantity=quantity,
        idempotency_key=idempotency_key,
        status=status,
    )


class InventoryTransactionAggregateTest:
    def test_create_with_valid_parameters(
        self, tenant_id: uuid4, sku_id: uuid4, warehouse_id: uuid4
    ) -> None:
        tx = InventoryTransactionAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            transaction_type=TransactionType.PURCHASE_RECEIPT,
            quantity=100.0,
            idempotency_key="idem-001",
            correlation_id="corr-1",
            document_id=uuid4(),
            document_type="purchase_order",
        )
        assert tx.tenant_id == tenant_id
        assert tx.sku_id == sku_id
        assert tx.warehouse_id == warehouse_id
        assert tx.transaction_type == TransactionType.PURCHASE_RECEIPT
        assert tx.quantity == 100.0
        assert tx.idempotency_key == "idem-001"
        assert tx.status == TransactionStatus.PENDING
        assert tx.direction == Direction.INBOUND
        assert tx.is_inbound() is True
        assert tx.is_outbound() is False

    def test_quantity_must_be_positive(self) -> None:
        with pytest.raises(INVError) as exc:
            _make_transaction(quantity=0.0)
        assert exc.value.code == INVErrorCode.LEDGER_FIELD_REQUIRED

    def test_negative_quantity_rejected(self) -> None:
        with pytest.raises(INVError) as exc:
            _make_transaction(quantity=-10.0)
        assert exc.value.code == INVErrorCode.LEDGER_FIELD_REQUIRED

    def test_idempotency_key_required(self) -> None:
        with pytest.raises(INVError) as exc:
            _make_transaction(idempotency_key="")
        assert exc.value.code == INVErrorCode.IDEMPOTENCY_KEY_REQUIRED

    def test_state_machine_pending_to_executing_to_completed(self) -> None:
        tx = _make_transaction()
        tx.execute()
        assert tx.status == TransactionStatus.EXECUTING
        ledger_id = uuid4()
        tx.complete(ledger_id)
        assert tx.status == TransactionStatus.COMPLETED
        assert tx.result_ledger_id == ledger_id

    def test_state_machine_pending_to_cancelled(self) -> None:
        tx = _make_transaction()
        tx.cancel()
        assert tx.status == TransactionStatus.CANCELLED

    def test_state_machine_executing_to_failed(self) -> None:
        tx = _make_transaction()
        tx.execute()
        tx.fail()
        assert tx.status == TransactionStatus.FAILED

    def test_state_machine_failed_can_retry_to_pending(self) -> None:
        tx = _make_transaction()
        tx.execute()
        tx.fail()
        assert tx.status == TransactionStatus.FAILED
        tx._transition(TransactionStatus.PENDING)
        assert tx.status == TransactionStatus.PENDING
        tx.execute()
        assert tx.status == TransactionStatus.EXECUTING

    def test_illegal_transition_pending_to_completed(self) -> None:
        tx = _make_transaction()
        with pytest.raises(INVError) as exc:
            tx.complete(uuid4())
        assert exc.value.code == INVErrorCode.INVALID_STATE_TRANSITION

    def test_illegal_transition_completed_to_executing(self) -> None:
        tx = _make_transaction()
        tx.execute()
        tx.complete(uuid4())
        with pytest.raises(INVError) as exc:
            tx.execute()
        assert exc.value.code == INVErrorCode.INVALID_STATE_TRANSITION

    def test_illegal_transition_cancelled_to_executing(self) -> None:
        tx = _make_transaction()
        tx.cancel()
        with pytest.raises(INVError) as exc:
            tx.execute()
        assert exc.value.code == INVErrorCode.INVALID_STATE_TRANSITION

    def test_illegal_transition_executing_to_cancelled(self) -> None:
        tx = _make_transaction()
        tx.execute()
        with pytest.raises(INVError) as exc:
            tx.cancel()
        assert exc.value.code == INVErrorCode.INVALID_STATE_TRANSITION

    def test_complete_sets_result_ledger_id(self) -> None:
        tx = _make_transaction()
        tx.execute()
        ledger_id = uuid4()
        tx.complete(ledger_id)
        assert tx.result_ledger_id == ledger_id

    def test_optional_properties_access(self) -> None:
        correlation_id = "corr-9"
        document_id = uuid4()
        organization_id = uuid4()
        site_id = uuid4()
        location_id = uuid4()
        tx = InventoryTransactionAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            sku_id=uuid4(),
            warehouse_id=uuid4(),
            transaction_type=TransactionType.SALES_ISSUE,
            quantity=10.0,
            idempotency_key="idem-p",
            correlation_id=correlation_id,
            document_id=document_id,
            document_type="sales_order",
            organization_id=organization_id,
            site_id=site_id,
            location_id=location_id,
        )
        assert tx.correlation_id == correlation_id
        assert tx.document_id == document_id
        assert tx.document_type == "sales_order"
        assert tx.organization_id == organization_id
        assert tx.site_id == site_id
        assert tx.location_id == location_id

    @pytest.mark.parametrize(
        "tx_type",
        [
            TransactionType.PURCHASE_RECEIPT,
            TransactionType.TRANSFER_IN,
            TransactionType.ADJUSTMENT_IN,
            TransactionType.RETURN_IN,
            TransactionType.INSPECT_PASS,
            TransactionType.UNBLOCK,
        ],
    )
    def test_direction_of_inbound_types(self, tx_type: TransactionType) -> None:
        assert direction_of(tx_type) == Direction.INBOUND
        tx = _make_transaction(transaction_type=tx_type)
        assert tx.is_inbound() is True
        assert tx.is_outbound() is False

    @pytest.mark.parametrize(
        "tx_type",
        [
            TransactionType.SALES_ISSUE,
            TransactionType.TRANSFER_OUT,
            TransactionType.ADJUSTMENT_OUT,
            TransactionType.RETURN_OUT,
            TransactionType.INSPECT_FAIL,
            TransactionType.BLOCK,
        ],
    )
    def test_direction_of_outbound_types(self, tx_type: TransactionType) -> None:
        assert direction_of(tx_type) == Direction.OUTBOUND
        tx = _make_transaction(transaction_type=tx_type)
        assert tx.is_outbound() is True
        assert tx.is_inbound() is False


class OwnershipTest:
    def test_validate_passes_with_tenant(self) -> None:
        tenant_id = uuid4()
        ownership = Ownership(tenant_id=tenant_id)
        ownership.validate()

    def test_validate_raises_when_tenant_none(self) -> None:
        ownership = Ownership(tenant_id=None)
        with pytest.raises(ValueError):
            ownership.validate()

    def test_belongs_to_tenant_true_when_match(self) -> None:
        tenant_id = uuid4()
        ownership = Ownership(tenant_id=tenant_id)
        assert ownership.belongs_to_tenant(tenant_id) is True

    def test_belongs_to_tenant_false_when_mismatch(self) -> None:
        ownership = Ownership(tenant_id=uuid4())
        assert ownership.belongs_to_tenant(uuid4()) is False