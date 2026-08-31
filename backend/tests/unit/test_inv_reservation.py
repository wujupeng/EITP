"""EITP-INV-001 库存预留聚合根单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.inventory.aggregates.inventory_reservation_aggregate import (
    InventoryReservationAggregate,
)
from app.domain.inventory.value_objects.shared import ReservationStatus
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
def document_id() -> uuid4:
    return uuid4()


def _make_reservation(
    *,
    tenant_id: uuid4 | None = None,
    sku_id: uuid4 | None = None,
    warehouse_id: uuid4 | None = None,
    reserved_quantity: float = 100.0,
    document_id: uuid4 | None = None,
    document_type: str = "sales_order",
    idempotency_key: str = "idem-res-1",
    expires_at: datetime | None = None,
    status: ReservationStatus = ReservationStatus.ACTIVE,
) -> InventoryReservationAggregate:
    return InventoryReservationAggregate(
        id=EntityId.generate(),
        tenant_id=tenant_id or uuid4(),
        sku_id=sku_id or uuid4(),
        warehouse_id=warehouse_id or uuid4(),
        reserved_quantity=reserved_quantity,
        document_id=document_id or uuid4(),
        document_type=document_type,
        idempotency_key=idempotency_key,
        expires_at=expires_at,
        status=status,
    )


class InventoryReservationAggregateTest:
    def test_create_with_valid_parameters(
        self, tenant_id: uuid4, sku_id: uuid4, warehouse_id: uuid4, document_id: uuid4
    ) -> None:
        reservation = InventoryReservationAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            reserved_quantity=100.0,
            document_id=document_id,
            document_type="sales_order",
            idempotency_key="idem-001",
        )
        assert reservation.tenant_id == tenant_id
        assert reservation.sku_id == sku_id
        assert reservation.warehouse_id == warehouse_id
        assert reservation.reserved_quantity == 100.0
        assert reservation.remaining_quantity == 100.0
        assert reservation.document_id == document_id
        assert reservation.document_type == "sales_order"
        assert reservation.idempotency_key == "idem-001"
        assert reservation.status == ReservationStatus.ACTIVE
        assert reservation.is_active() is True

    def test_reserved_quantity_must_be_positive(self) -> None:
        with pytest.raises(INVError) as exc:
            _make_reservation(reserved_quantity=0.0)
        assert exc.value.code == INVErrorCode.INSUFFICIENT_AVAILABLE

    def test_negative_reserved_quantity_rejected(self) -> None:
        with pytest.raises(INVError) as exc:
            _make_reservation(reserved_quantity=-10.0)
        assert exc.value.code == INVErrorCode.INSUFFICIENT_AVAILABLE

    def test_consume_partial_keeps_active(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.consume(30.0)
        assert reservation.remaining_quantity == 70.0
        assert reservation.status == ReservationStatus.ACTIVE
        assert reservation.is_active() is True

    def test_consume_full_transitions_to_consumed(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.consume(100.0)
        assert reservation.remaining_quantity == 0.0
        assert reservation.status == ReservationStatus.CONSUMED

    def test_consume_in_two_steps_full_transitions_to_consumed(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.consume(40.0)
        assert reservation.status == ReservationStatus.ACTIVE
        reservation.consume(60.0)
        assert reservation.remaining_quantity == 0.0
        assert reservation.status == ReservationStatus.CONSUMED

    def test_consume_over_consume_rejected(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.consume(70.0)
        with pytest.raises(INVError) as exc:
            reservation.consume(50.0)
        assert exc.value.code == INVErrorCode.INSUFFICIENT_AVAILABLE
        assert reservation.remaining_quantity == 30.0

    def test_consume_on_released_rejected(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.release()
        with pytest.raises(INVError) as exc:
            reservation.consume(10.0)
        assert exc.value.code == INVErrorCode.RESERVATION_ALREADY_RELEASED

    def test_consume_on_consumed_rejected(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.consume(100.0)
        with pytest.raises(INVError) as exc:
            reservation.consume(10.0)
        assert exc.value.code == INVErrorCode.RESERVATION_ALREADY_RELEASED

    def test_release_without_quantity_transitions_to_released(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.release()
        assert reservation.remaining_quantity == 0.0
        assert reservation.status == ReservationStatus.RELEASED

    def test_release_with_partial_quantity_keeps_active(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.release(40.0)
        assert reservation.remaining_quantity == 60.0
        assert reservation.status == ReservationStatus.ACTIVE

    def test_release_with_full_quantity_transitions_to_released(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.release(100.0)
        assert reservation.remaining_quantity == 0.0
        assert reservation.status == ReservationStatus.RELEASED

    def test_release_clamps_to_remaining(self) -> None:
        reservation = _make_reservation(reserved_quantity=50.0)
        reservation.release(200.0)
        assert reservation.remaining_quantity == 0.0
        assert reservation.status == ReservationStatus.RELEASED

    def test_release_on_released_rejected(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.release()
        with pytest.raises(INVError) as exc:
            reservation.release()
        assert exc.value.code == INVErrorCode.RESERVATION_ALREADY_RELEASED

    def test_mark_expired_transitions_active_to_expired(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.mark_expired()
        assert reservation.status == ReservationStatus.EXPIRED
        assert reservation.remaining_quantity == 0.0

    def test_mark_expired_on_released_is_noop(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.release()
        reservation.mark_expired()
        assert reservation.status == ReservationStatus.RELEASED

    def test_mark_expired_on_consumed_is_noop(self) -> None:
        reservation = _make_reservation(reserved_quantity=100.0)
        reservation.consume(100.0)
        reservation.mark_expired()
        assert reservation.status == ReservationStatus.CONSUMED

    def test_is_expired_true_when_past_expires_at(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        reservation = _make_reservation(expires_at=past)
        assert reservation.is_expired() is True

    def test_is_expired_false_when_future_expires_at(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        reservation = _make_reservation(expires_at=future)
        assert reservation.is_expired() is False

    def test_is_expired_false_when_no_expiry(self) -> None:
        reservation = _make_reservation(expires_at=None)
        assert reservation.is_expired() is False

    def test_expires_at_property_access(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        reservation = _make_reservation(expires_at=future)
        assert reservation.expires_at == future