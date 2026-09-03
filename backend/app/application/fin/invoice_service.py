"""FIN 发票应用服务 - InvoiceService。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.fin.aggregates.invoice_aggregate import (
    InvoiceAggregate,
    InvoiceLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.services.invoice_matching_engine import (
    InvoiceMatchingEngine,
    MatchResult,
)
from app.domain.fin.value_objects.enums import InvoiceType
from app.domain.fin.value_objects.money import Money
from app.infrastructure.fin.invoice_archive_repository import InvoiceArchiveRepository
from app.infrastructure.fin.invoice_repository import InvoiceRepository

logger = get_logger(__name__)


class InvoiceService:
    """发票应用服务 - 开具/匹配/验真/归档/作废。"""

    def __init__(
        self,
        invoice_repo: InvoiceRepository,
        archive_repo: InvoiceArchiveRepository,
    ) -> None:
        self._invoice_repo = invoice_repo
        self._archive_repo = archive_repo

    async def issue_invoice(
        self,
        tenant_id: UUID,
        invoice_code: str,
        invoice_no: str,
        invoice_type: str,
        buyer_info: dict[str, str],
        seller_info: dict[str, str],
        lines: list[dict[str, Any]],
        currency: str = "CNY",
        red_original_invoice_no: str | None = None,
        image_storage_id: str | None = None,
    ) -> InvoiceAggregate:
        existing = await self._invoice_repo.get_by_no(invoice_no)
        if existing is not None:
            raise FINError(
                FINErrorCode.INVOICE_DUPLICATE,
                f"invoice {invoice_no} already exists",
            )
        domain_lines: list[InvoiceLine] = []
        for idx, ln in enumerate(lines, start=1):
            domain_lines.append(
                InvoiceLine(
                    line_no=ln.get("line_no", idx),
                    product_id=ln["product_id"],
                    product_name=ln["product_name"],
                    quantity=Decimal(str(ln["quantity"])),
                    tax_exclusive_amount=Money(
                        Decimal(str(ln["tax_exclusive_amount"])), currency
                    ),
                    tax_amount=Money(Decimal(str(ln["tax_amount"])), currency),
                    tax_inclusive_amount=Money(
                        Decimal(str(ln["tax_inclusive_amount"])), currency
                    ),
                )
            )
        invoice = InvoiceAggregate.create(
            invoice_code=invoice_code,
            invoice_no=invoice_no,
            invoice_type=InvoiceType(invoice_type),
            buyer_info=buyer_info,
            seller_info=seller_info,
            lines=domain_lines,
            tenant_id=tenant_id,
            red_original_invoice_no=red_original_invoice_no,
            image_storage_id=image_storage_id,
        )
        issued = invoice.issue()
        await self._invoice_repo.save(issued)
        logger.info("invoice_issued", invoice_no=invoice_no, invoice_type=invoice_type)
        return issued

    async def match_invoice(
        self,
        tenant_id: UUID,
        invoice_no: str,
        candidates: list[dict[str, Any]],
    ) -> MatchResult:
        invoice = await self._invoice_repo.get_by_no(invoice_no)
        if invoice is None:
            raise FINError(
                FINErrorCode.INVOICE_NOT_FOUND,
                f"invoice {invoice_no} not found",
            )
        best = InvoiceMatchingEngine.best_match(invoice, candidates)
        if best is None:
            raise FINError(
                FINErrorCode.INVOICE_VERIFY_FAIL,
                f"invoice {invoice_no} no match found among {len(candidates)} candidates",
            )
        matched = invoice.match(
            best.business_ref_type or "", best.business_ref_id or ""
        )
        await self._invoice_repo.save(matched)
        logger.info(
            "invoice_matched",
            invoice_no=invoice_no,
            business_ref_type=best.business_ref_type,
            business_ref_id=best.business_ref_id,
            score=best.score,
        )
        return best

    async def verify_invoice(
        self, tenant_id: UUID, invoice_no: str
    ) -> InvoiceAggregate:
        invoice = await self._invoice_repo.get_by_no(invoice_no)
        if invoice is None:
            raise FINError(
                FINErrorCode.INVOICE_NOT_FOUND,
                f"invoice {invoice_no} not found",
            )
        verified = invoice.verify()
        await self._invoice_repo.save(verified)
        logger.info("invoice_verified", invoice_no=invoice_no)
        return verified

    async def archive_invoice(
        self, tenant_id: UUID, invoice_no: str
    ) -> InvoiceAggregate:
        invoice = await self._invoice_repo.get_by_no(invoice_no)
        if invoice is None:
            raise FINError(
                FINErrorCode.INVOICE_NOT_FOUND,
                f"invoice {invoice_no} not found",
            )
        archived = invoice.archive()
        await self._invoice_repo.save(archived)
        await self._archive_repo.archive(
            invoice_id=archived.invoice_id,
            tenant_id=tenant_id,
            archive_hash=archived.archive_hash or "",
            archive_payload=archived._archive_payload(),
            image_storage_id=archived.image_storage_id,
        )
        logger.info(
            "invoice_archived",
            invoice_no=invoice_no,
            archive_hash=archived.archive_hash,
        )
        return archived

    async def void_invoice(
        self, tenant_id: UUID, invoice_no: str, reason: str
    ) -> InvoiceAggregate:
        invoice = await self._invoice_repo.get_by_no(invoice_no)
        if invoice is None:
            raise FINError(
                FINErrorCode.INVOICE_NOT_FOUND,
                f"invoice {invoice_no} not found",
            )
        voided = invoice.void_invoice(reason)
        await self._invoice_repo.save(voided)
        logger.info("invoice_voided", invoice_no=invoice_no, reason=reason)
        return voided