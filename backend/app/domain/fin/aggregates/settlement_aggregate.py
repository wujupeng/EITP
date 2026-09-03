"""FIN 结算聚合根 - SettlementAggregate + SettlementLine。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import SettlementStatus, SettlementType
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class SettlementLine:
    """结算明细行 - 含税单价/不含税单价/数量/税率。"""

    line_no: int
    product_id: str
    quantity: Decimal
    tax_exclusive_unit_price: Money
    tax_inclusive_unit_price: Money
    tax_rate: Decimal

    def line_settlement_amount(self) -> Money:
        return self.tax_inclusive_unit_price.multiply(self.quantity)

    def line_tax_amount(self) -> Money:
        base = self.tax_exclusive_unit_price.multiply(self.quantity)
        return base.multiply(self.tax_rate)


@dataclass(frozen=True)
class SettlementAggregate:
    """结算聚合根 - 金额守恒与状态机。"""

    settlement_id: UUID
    settlement_no: str
    settlement_type: SettlementType
    status: SettlementStatus
    counterparty_id: str
    counterparty_type: str
    settlement_lines: tuple[SettlementLine, ...]
    settlement_amount: Money
    tax_amount: Money
    currency: str
    initiator_tenant_id: UUID
    receiver_tenant_id: UUID | None
    related_order_type: str | None
    related_order_id: str | None
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        settlement_no: str,
        settlement_type: SettlementType,
        counterparty_id: str,
        counterparty_type: str,
        lines: list[SettlementLine] | tuple[SettlementLine, ...],
        currency: str,
        tenant_id: UUID,
        initiator_tenant_id: UUID | None = None,
        receiver_tenant_id: UUID | None = None,
        related_order_type: str | None = None,
        related_order_id: str | None = None,
    ) -> SettlementAggregate:
        if not lines:
            raise FINError(
                FINErrorCode.SETTLEMENT_LINE_EMPTY,
                f"settlement {settlement_no} lines empty",
            )
        line_tuple = tuple(lines)
        settlement_total = line_tuple[0].line_settlement_amount()
        for ln in line_tuple[1:]:
            settlement_total = settlement_total.add(ln.line_settlement_amount())
        tax_total = line_tuple[0].line_tax_amount()
        for ln in line_tuple[1:]:
            tax_total = tax_total.add(ln.line_tax_amount())
        return cls(
            settlement_id=uuid4(),
            settlement_no=settlement_no,
            settlement_type=settlement_type,
            status=SettlementStatus.DRAFT,
            counterparty_id=counterparty_id,
            counterparty_type=counterparty_type,
            settlement_lines=line_tuple,
            settlement_amount=settlement_total,
            tax_amount=tax_total,
            currency=currency,
            initiator_tenant_id=initiator_tenant_id or tenant_id,
            receiver_tenant_id=receiver_tenant_id,
            related_order_type=related_order_type,
            related_order_id=related_order_id,
            tenant_id=tenant_id,
        )

    def _check_transition(self, expected: SettlementStatus) -> None:
        if self.status != expected:
            raise FINError(
                FINErrorCode.SETTLEMENT_INVALID_TRANSITION,
                f"settlement {self.settlement_no} invalid transition: "
                f"{self.status.value} -> expected {expected.value}",
            )

    def confirm(self) -> SettlementAggregate:
        self._check_transition(SettlementStatus.DRAFT)
        return dataclass_replace(
            self,
            status=SettlementStatus.CONFIRMED,
            updated_at=datetime.now(timezone.utc),
        )

    def mark_settled(self) -> SettlementAggregate:
        self._check_transition(SettlementStatus.CONFIRMED)
        return dataclass_replace(
            self,
            status=SettlementStatus.SETTLED,
            updated_at=datetime.now(timezone.utc),
        )

    def close(self) -> SettlementAggregate:
        self._check_transition(SettlementStatus.SETTLED)
        return dataclass_replace(
            self,
            status=SettlementStatus.CLOSED,
            updated_at=datetime.now(timezone.utc),
        )

    def cancel(self) -> SettlementAggregate:
        if self.status not in (SettlementStatus.DRAFT, SettlementStatus.CONFIRMED):
            raise FINError(
                FINErrorCode.SETTLEMENT_INVALID_TRANSITION,
                f"settlement {self.settlement_no} cannot cancel from {self.status.value}",
            )
        return dataclass_replace(
            self,
            status=SettlementStatus.CANCELLED,
            updated_at=datetime.now(timezone.utc),
        )