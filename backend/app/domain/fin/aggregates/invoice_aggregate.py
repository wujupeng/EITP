"""FIN 发票聚合根 - InvoiceAggregate + InvoiceLine。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import InvoiceStatus, InvoiceType
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class InvoiceLine:
    """发票明细行 - 不含税/税额/价税合计。"""

    line_no: int
    product_id: str
    product_name: str
    quantity: Decimal
    tax_exclusive_amount: Money
    tax_amount: Money
    tax_inclusive_amount: Money


@dataclass(frozen=True)
class InvoiceAggregate:
    """发票聚合根 - 状态机 + 金额校验 + SHA-256 归档。"""

    invoice_id: UUID
    invoice_code: str
    invoice_no: str
    invoice_type: InvoiceType
    status: InvoiceStatus
    buyer_info: dict[str, str]
    seller_info: dict[str, str]
    invoice_lines: tuple[InvoiceLine, ...]
    tax_exclusive_amount: Money
    tax_amount: Money
    tax_inclusive_amount: Money
    red_original_invoice_no: str | None
    archive_hash: str | None
    image_storage_id: str | None
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        invoice_code: str,
        invoice_no: str,
        invoice_type: InvoiceType,
        buyer_info: dict[str, str],
        seller_info: dict[str, str],
        lines: list[InvoiceLine] | tuple[InvoiceLine, ...],
        tenant_id: UUID,
        red_original_invoice_no: str | None = None,
        image_storage_id: str | None = None,
    ) -> InvoiceAggregate:
        if not lines:
            raise FINError(
                FINErrorCode.INVOICE_AMOUNT_MISMATCH,
                f"invoice {invoice_no} lines empty",
            )
        line_tuple = tuple(lines)
        currency = line_tuple[0].tax_inclusive_amount.currency
        tax_exclusive_total = line_tuple[0].tax_exclusive_amount
        tax_total = line_tuple[0].tax_amount
        tax_inclusive_total = line_tuple[0].tax_inclusive_amount
        for ln in line_tuple[1:]:
            tax_exclusive_total = tax_exclusive_total.add(ln.tax_exclusive_amount)
            tax_total = tax_total.add(ln.tax_amount)
            tax_inclusive_total = tax_inclusive_total.add(ln.tax_inclusive_amount)
        expected_inclusive = tax_exclusive_total.add(tax_total)
        if tax_inclusive_total != expected_inclusive:
            raise FINError(
                FINErrorCode.INVOICE_AMOUNT_MISMATCH,
                f"invoice {invoice_no} line total mismatch: "
                f"tax_inclusive {tax_inclusive_total} != "
                f"tax_exclusive {tax_exclusive_total} + tax {tax_total}",
            )
        if invoice_type == InvoiceType.RED and not red_original_invoice_no:
            raise FINError(
                FINErrorCode.INVOICE_RED_INVALID,
                f"red invoice {invoice_no} requires original invoice no",
            )
        return cls(
            invoice_id=uuid4(),
            invoice_code=invoice_code,
            invoice_no=invoice_no,
            invoice_type=invoice_type,
            status=InvoiceStatus.DRAFT,
            buyer_info=buyer_info,
            seller_info=seller_info,
            invoice_lines=line_tuple,
            tax_exclusive_amount=tax_exclusive_total,
            tax_amount=tax_total,
            tax_inclusive_amount=tax_inclusive_total,
            red_original_invoice_no=red_original_invoice_no,
            archive_hash=None,
            image_storage_id=image_storage_id,
            tenant_id=tenant_id,
        )

    def _check_transition(self, expected: InvoiceStatus) -> None:
        if self.status != expected:
            raise FINError(
                FINErrorCode.INVOICE_ARCHIVED_IMMUTABLE,
                f"invoice {self.invoice_no} invalid transition: "
                f"{self.status.value} -> expected {expected.value}",
            )

    def issue(self) -> InvoiceAggregate:
        self._check_transition(InvoiceStatus.DRAFT)
        return dataclass_replace(
            self,
            status=InvoiceStatus.ISSUED,
            updated_at=datetime.now(timezone.utc),
        )

    def match(
        self, business_ref_type: str, business_ref_id: str
    ) -> InvoiceAggregate:
        self._check_transition(InvoiceStatus.ISSUED)
        return dataclass_replace(
            self,
            status=InvoiceStatus.MATCHED,
            updated_at=datetime.now(timezone.utc),
        )

    def verify(self) -> InvoiceAggregate:
        self._check_transition(InvoiceStatus.MATCHED)
        return dataclass_replace(
            self,
            status=InvoiceStatus.VERIFIED,
            updated_at=datetime.now(timezone.utc),
        )

    def archive(self) -> InvoiceAggregate:
        self._check_transition(InvoiceStatus.VERIFIED)
        payload = self._archive_payload()
        archive_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return dataclass_replace(
            self,
            status=InvoiceStatus.ARCHIVED,
            archive_hash=archive_hash,
            updated_at=datetime.now(timezone.utc),
        )

    def void_invoice(self, reason: str) -> InvoiceAggregate:
        if not reason:
            raise FINError(
                FINErrorCode.INVOICE_VOID_REASON_REQUIRED,
                f"invoice {self.invoice_no} void reason required",
            )
        if self.status == InvoiceStatus.ARCHIVED:
            raise FINError(
                FINErrorCode.INVOICE_ARCHIVED_VOID_FORBIDDEN,
                f"archived invoice {self.invoice_no} cannot be voided",
            )
        if self.status == InvoiceStatus.VOID:
            raise FINError(
                FINErrorCode.INVOICE_ARCHIVED_IMMUTABLE,
                f"invoice {self.invoice_no} already void",
            )
        return dataclass_replace(
            self,
            status=InvoiceStatus.VOID,
            updated_at=datetime.now(timezone.utc),
        )

    def _archive_payload(self) -> str:
        parts = [
            self.invoice_code,
            self.invoice_no,
            self.invoice_type.value,
            str(self.tax_exclusive_amount.amount),
            str(self.tax_amount.amount),
            str(self.tax_inclusive_amount.amount),
        ]
        for ln in self.invoice_lines:
            parts.append(
                f"{ln.line_no}:{ln.product_id}:{ln.quantity}:"
                f"{ln.tax_exclusive_amount.amount}:{ln.tax_amount.amount}:"
                f"{ln.tax_inclusive_amount.amount}"
            )
        return "|".join(parts)