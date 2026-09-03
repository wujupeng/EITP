"""FIN 结算应用服务 - SettlementService。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.fin.aggregates.ap_voucher_aggregate import APVoucherAggregate
from app.domain.fin.aggregates.ar_voucher_aggregate import ARVoucherAggregate
from app.domain.fin.aggregates.settlement_aggregate import (
    SettlementAggregate,
    SettlementLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import SettlementType, VoucherType
from app.domain.fin.value_objects.money import Money
from app.infrastructure.fin.ap_voucher_repository import APVoucherRepository
from app.infrastructure.fin.ar_voucher_repository import ARVoucherRepository
from app.infrastructure.fin.pur_order_read_view import PurOrderReadView
from app.infrastructure.fin.sal_order_read_view import SalOrderReadView
from app.infrastructure.fin.settlement_repository import SettlementRepository

logger = get_logger(__name__)


class SettlementService:
    """结算应用服务 - 创建/确认/取消结算 + 跨租户结算 + 自动生成 AR/AP 凭证。"""

    def __init__(
        self,
        settlement_repo: SettlementRepository,
        ar_repo: ARVoucherRepository,
        ap_repo: APVoucherRepository,
        pur_read_view: PurOrderReadView,
        sal_read_view: SalOrderReadView,
    ) -> None:
        self._settlement_repo = settlement_repo
        self._ar_repo = ar_repo
        self._ap_repo = ap_repo
        self._pur_read_view = pur_read_view
        self._sal_read_view = sal_read_view

    async def create_settlement(
        self,
        tenant_id: UUID,
        settlement_no: str,
        settlement_type: str,
        counterparty_id: str,
        counterparty_type: str,
        currency: str,
        lines: list[dict[str, Any]],
        related_order_type: str | None = None,
        related_order_id: str | None = None,
        receiver_tenant_id: UUID | None = None,
    ) -> SettlementAggregate:
        existing = await self._settlement_repo.get_by_no(settlement_no)
        if existing is not None:
            raise FINError(
                FINErrorCode.SETTLEMENT_DUPLICATE,
                f"settlement {settlement_no} already exists",
            )
        st_type = SettlementType(settlement_type)
        if st_type == SettlementType.PURCHASE and related_order_id:
            await self._validate_purchase_settlement(related_order_id, lines)
        elif st_type == SettlementType.SALES and related_order_id:
            await self._validate_sales_settlement(related_order_id, lines)
        domain_lines: list[SettlementLine] = []
        for idx, ln in enumerate(lines, start=1):
            domain_lines.append(
                SettlementLine(
                    line_no=ln.get("line_no", idx),
                    product_id=ln["product_id"],
                    quantity=Decimal(str(ln["quantity"])),
                    tax_exclusive_unit_price=Money(
                        Decimal(str(ln["tax_exclusive_unit_price"])), currency
                    ),
                    tax_inclusive_unit_price=Money(
                        Decimal(str(ln["tax_inclusive_unit_price"])), currency
                    ),
                    tax_rate=Decimal(str(ln["tax_rate"])),
                )
            )
        settlement = SettlementAggregate.create(
            settlement_no=settlement_no,
            settlement_type=st_type,
            counterparty_id=counterparty_id,
            counterparty_type=counterparty_type,
            lines=domain_lines,
            currency=currency,
            tenant_id=tenant_id,
            receiver_tenant_id=receiver_tenant_id,
            related_order_type=related_order_type,
            related_order_id=related_order_id,
        )
        await self._settlement_repo.save(settlement)
        logger.info(
            "settlement_created",
            settlement_no=settlement_no,
            settlement_type=settlement_type,
            amount=str(settlement.settlement_amount.amount),
        )
        return settlement

    async def _validate_purchase_settlement(
        self, order_no: str, lines: list[dict[str, Any]]
    ) -> None:
        order = await self._pur_read_view.query(order_no)
        if order is None:
            raise FINError(
                FINErrorCode.SETTLEMENT_PUR_NOT_RECEIVED,
                f"purchase order {order_no} not found",
            )
        if not order.get("is_fully_received"):
            raise FINError(
                FINErrorCode.SETTLEMENT_PUR_NOT_RECEIVED,
                f"purchase order {order_no} not fully received",
            )
        for ln in lines:
            received = await self._pur_read_view.get_received_quantity(
                order_no, ln["product_id"]
            )
            if received is None or Decimal(str(received)) < Decimal(str(ln["quantity"])):
                raise FINError(
                    FINErrorCode.SETTLEMENT_QTY_EXCEED_RECEIVED,
                    f"settlement qty {ln['quantity']} exceeds received {received} "
                    f"for product {ln['product_id']} in order {order_no}",
                )

    async def _validate_sales_settlement(
        self, order_no: str, lines: list[dict[str, Any]]
    ) -> None:
        order = await self._sal_read_view.query(order_no)
        if order is None:
            raise FINError(
                FINErrorCode.SETTLEMENT_SAL_NOT_SHIPPED,
                f"sales order {order_no} not found",
            )
        if not order.get("is_fully_shipped"):
            raise FINError(
                FINErrorCode.SETTLEMENT_SAL_NOT_SHIPPED,
                f"sales order {order_no} not fully shipped",
            )
        for ln in lines:
            shipped = await self._sal_read_view.get_shipped_quantity(
                order_no, ln["product_id"]
            )
            if shipped is None or Decimal(str(shipped)) < Decimal(str(ln["quantity"])):
                raise FINError(
                    FINErrorCode.SETTLEMENT_QTY_EXCEED_RECEIVED,
                    f"settlement qty {ln['quantity']} exceeds shipped {shipped} "
                    f"for product {ln['product_id']} in order {order_no}",
                )

    async def confirm_settlement(
        self, tenant_id: UUID, settlement_no: str
    ) -> SettlementAggregate:
        settlement = await self._settlement_repo.get_by_no(settlement_no)
        if settlement is None:
            raise FINError(
                FINErrorCode.SETTLEMENT_NOT_FOUND,
                f"settlement {settlement_no} not found",
            )
        confirmed = settlement.confirm()
        await self._settlement_repo.save(confirmed)
        await self._generate_vouchers(confirmed)
        logger.info("settlement_confirmed", settlement_no=settlement_no)
        return confirmed

    async def confirm_cross_tenant_settlement(
        self,
        tenant_id: UUID,
        settlement_no: str,
        initiator_tenant_id: UUID,
        receiver_tenant_id: UUID,
    ) -> SettlementAggregate:
        settlement = await self._settlement_repo.get_by_no(settlement_no)
        if settlement is None:
            raise FINError(
                FINErrorCode.SETTLEMENT_NOT_FOUND,
                f"settlement {settlement_no} not found",
            )
        if settlement.settlement_type != SettlementType.CROSS_TENANT:
            raise FINError(
                FINErrorCode.SETTLEMENT_CROSS_TENANT_NOT_CONFIRMED,
                f"settlement {settlement_no} is not cross-tenant type",
            )
        if settlement.receiver_tenant_id is None:
            raise FINError(
                FINErrorCode.SETTLEMENT_CROSS_TENANT_NOT_CONFIRMED,
                f"settlement {settlement_no} receiver tenant not set",
            )
        confirmed = settlement.confirm()
        await self._settlement_repo.save(confirmed)
        await self._generate_vouchers(confirmed)
        logger.info(
            "cross_tenant_settlement_confirmed",
            settlement_no=settlement_no,
            initiator=str(initiator_tenant_id),
            receiver=str(receiver_tenant_id),
        )
        return confirmed

    async def cancel_settlement(
        self, tenant_id: UUID, settlement_no: str, reason: str = ""
    ) -> SettlementAggregate:
        settlement = await self._settlement_repo.get_by_no(settlement_no)
        if settlement is None:
            raise FINError(
                FINErrorCode.SETTLEMENT_NOT_FOUND,
                f"settlement {settlement_no} not found",
            )
        cancelled = settlement.cancel()
        await self._settlement_repo.save(cancelled)
        logger.info("settlement_cancelled", settlement_no=settlement_no, reason=reason)
        return cancelled

    async def _generate_vouchers(self, settlement: SettlementAggregate) -> None:
        if settlement.settlement_type == SettlementType.SALES:
            ar_no = f"AR-{settlement.settlement_no}"
            ar_voucher = ARVoucherAggregate.create(
                voucher_no=ar_no,
                business_ref_type="SETTLEMENT",
                business_ref_id=settlement.settlement_no,
                receivable_amount=settlement.settlement_amount,
                tenant_id=settlement.tenant_id,
                due_date=date.today(),
            )
            await self._ar_repo.save(ar_voucher)
        elif settlement.settlement_type == SettlementType.PURCHASE:
            ap_no = f"AP-{settlement.settlement_no}"
            ap_voucher = APVoucherAggregate.create(
                voucher_no=ap_no,
                business_ref_type="SETTLEMENT",
                business_ref_id=settlement.settlement_no,
                payable_amount=settlement.settlement_amount,
                tenant_id=settlement.tenant_id,
                due_date=date.today(),
            )
            await self._ap_repo.save(ap_voucher)
        elif settlement.settlement_type == SettlementType.CROSS_TENANT:
            if settlement.receiver_tenant_id is not None:
                ar_no = f"AR-{settlement.settlement_no}"
                ar_voucher = ARVoucherAggregate.create(
                    voucher_no=ar_no,
                    business_ref_type="SETTLEMENT",
                    business_ref_id=settlement.settlement_no,
                    receivable_amount=settlement.settlement_amount,
                    tenant_id=settlement.receiver_tenant_id,
                    due_date=date.today(),
                )
                await self._ar_repo.save(ar_voucher)
            ap_no = f"AP-{settlement.settlement_no}"
            ap_voucher = APVoucherAggregate.create(
                voucher_no=ap_no,
                business_ref_type="SETTLEMENT",
                business_ref_id=settlement.settlement_no,
                payable_amount=settlement.settlement_amount,
                tenant_id=settlement.initiator_tenant_id,
                due_date=date.today(),
            )
            await self._ap_repo.save(ap_voucher)