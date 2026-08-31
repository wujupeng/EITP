"""库存预留聚合根 - 状态机 + 部分核销支持。

状态流转：active → released/consumed/expired
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.inventory.value_objects.shared import ReservationStatus
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


class InventoryReservationAggregate(AggregateRoot):
    """库存预留聚合根 - 预占库存，支持部分核销。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        reserved_quantity: float,
        document_id: UUID,
        document_type: str,
        idempotency_key: str,
        organization_id: UUID | None = None,
        site_id: UUID | None = None,
        location_id: UUID | None = None,
        expires_at: datetime | None = None,
        status: ReservationStatus = ReservationStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        if reserved_quantity <= 0:
            raise INVError(INVErrorCode.INSUFFICIENT_AVAILABLE, "预留数量必须为正数")
        self._tenant_id = tenant_id
        self._sku_id = sku_id
        self._warehouse_id = warehouse_id
        self._reserved_quantity = reserved_quantity
        self._remaining_quantity = reserved_quantity
        self._document_id = document_id
        self._document_type = document_type
        self._idempotency_key = idempotency_key
        self._organization_id = organization_id
        self._site_id = site_id
        self._location_id = location_id
        self._expires_at = expires_at
        self._status = status

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def sku_id(self) -> UUID:
        return self._sku_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def reserved_quantity(self) -> float:
        return self._reserved_quantity

    @property
    def remaining_quantity(self) -> float:
        return self._remaining_quantity

    @property
    def document_id(self) -> UUID:
        return self._document_id

    @property
    def document_type(self) -> str:
        return self._document_type

    @property
    def idempotency_key(self) -> str:
        return self._idempotency_key

    @property
    def expires_at(self) -> datetime | None:
        return self._expires_at

    @property
    def status(self) -> ReservationStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == ReservationStatus.ACTIVE

    def consume(self, quantity: float) -> None:
        if self._status != ReservationStatus.ACTIVE:
            raise INVError(
                INVErrorCode.RESERVATION_ALREADY_RELEASED,
                f"预留状态 {self._status.value} 不可核销",
            )
        if quantity > self._remaining_quantity:
            raise INVError(
                INVErrorCode.INSUFFICIENT_AVAILABLE,
                f"核销超量: {quantity} > {self._remaining_quantity}",
            )
        self._remaining_quantity -= quantity
        if self._remaining_quantity <= 0:
            self._status = ReservationStatus.CONSUMED
        self._touch()

    def release(self, quantity: float | None = None) -> None:
        if self._status != ReservationStatus.ACTIVE:
            raise INVError(
                INVErrorCode.RESERVATION_ALREADY_RELEASED,
                f"预留状态 {self._status.value} 不可释放",
            )
        if quantity is None:
            self._remaining_quantity = 0.0
            self._status = ReservationStatus.RELEASED
        else:
            self._remaining_quantity -= min(quantity, self._remaining_quantity)
            if self._remaining_quantity <= 0:
                self._status = ReservationStatus.RELEASED
        self._touch()

    def mark_expired(self) -> None:
        if self._status != ReservationStatus.ACTIVE:
            return
        self._status = ReservationStatus.EXPIRED
        self._remaining_quantity = 0.0
        self._touch()

    def is_expired(self) -> bool:
        if self._expires_at is None:
            return False
        return datetime.now(timezone.utc) > self._expires_at