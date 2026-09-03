"""FIN 对账应用服务 - ReconciliationService。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.fin.aggregates.reconciliation_aggregate import (
    ReconciliationAggregate,
    ReconciliationDifference,
    ReconciliationLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import DifferenceType, HandleStatus
from app.domain.fin.value_objects.money import Money
from app.infrastructure.fin.reconciliation_repository import (
    ReconciliationRepository,
)

logger = get_logger(__name__)


class ReconciliationService:
    """对账应用服务 - 创建/匹配/差异处理/报表。"""

    def __init__(self, recon_repo: ReconciliationRepository) -> None:
        self._recon_repo = recon_repo

    async def create_reconciliation(
        self,
        tenant_id: UUID,
        recon_no: str,
        period_start: date,
        period_end: date,
        scope_type: str,
        scope_value: str,
        data_source: str,
        currency: str,
        lines: list[dict[str, Any]] | None = None,
    ) -> ReconciliationAggregate:
        existing = await self._recon_repo.get_by_no(recon_no)
        if existing is not None:
            raise FINError(
                FINErrorCode.RECON_DUPLICATE,
                f"reconciliation {recon_no} already exists",
            )
        domain_lines: list[ReconciliationLine] = []
        if lines:
            for idx, ln in enumerate(lines, start=1):
                domain_lines.append(
                    ReconciliationLine(
                        line_no=ln.get("line_no", idx),
                        business_ref_type=ln["business_ref_type"],
                        business_ref_id=ln["business_ref_id"],
                        system_amount=Money(
                            Decimal(str(ln["system_amount"])), currency
                        ),
                        external_amount=Money(
                            Decimal(str(ln["external_amount"])), currency
                        ),
                        is_matched=ln.get("is_matched", False),
                    )
                )
        recon = ReconciliationAggregate.create(
            recon_no=recon_no,
            period_start=period_start,
            period_end=period_end,
            scope_type=scope_type,
            scope_value=scope_value,
            data_source=data_source,
            currency=currency,
            tenant_id=tenant_id,
            lines=domain_lines,
        )
        await self._recon_repo.save(recon)
        logger.info("recon_created", recon_no=recon_no)
        return recon

    async def start_matching(
        self, tenant_id: UUID, recon_no: str
    ) -> ReconciliationAggregate:
        recon = await self._recon_repo.get_by_no(recon_no)
        if recon is None:
            raise FINError(
                FINErrorCode.RECON_NOT_FOUND,
                f"reconciliation {recon_no} not found",
            )
        started = recon.start_matching()
        await self._recon_repo.save(started)
        logger.info("recon_matching_started", recon_no=recon_no)
        return started

    async def finish_matching(
        self,
        tenant_id: UUID,
        recon_no: str,
        differences: list[dict[str, Any]],
    ) -> ReconciliationAggregate:
        recon = await self._recon_repo.get_by_no(recon_no)
        if recon is None:
            raise FINError(
                FINErrorCode.RECON_NOT_FOUND,
                f"reconciliation {recon_no} not found",
            )
        domain_diffs: list[ReconciliationDifference] = []
        for diff in differences:
            domain_diffs.append(
                ReconciliationDifference(
                    diff_id=UUID(str(diff["diff_id"])),
                    line_no=diff["line_no"],
                    business_ref_type=diff["business_ref_type"],
                    business_ref_id=diff["business_ref_id"],
                    diff_type=DifferenceType(diff["diff_type"]),
                    diff_amount=Money(
                        Decimal(str(diff["diff_amount"])),
                        diff.get("currency", "CNY"),
                    ),
                    handle_status=HandleStatus.PENDING,
                )
            )
        finished = recon.finish_matching(domain_diffs)
        await self._recon_repo.save(finished)
        logger.info(
            "recon_matching_finished",
            recon_no=recon_no,
            diff_count=len(domain_diffs),
        )
        return finished

    async def handle_difference(
        self,
        tenant_id: UUID,
        recon_no: str,
        diff_id: UUID,
        handle_action: str,
        handler_id: str,
        handle_opinion: str,
    ) -> ReconciliationAggregate:
        recon = await self._recon_repo.get_by_no(recon_no)
        if recon is None:
            raise FINError(
                FINErrorCode.RECON_NOT_FOUND,
                f"reconciliation {recon_no} not found",
            )
        handled = recon.handle_diff(
            diff_id=diff_id,
            handle_action=handle_action,
            handler_id=handler_id,
            handle_opinion=handle_opinion,
        )
        await self._recon_repo.save(handled)
        logger.info(
            "recon_diff_handled",
            recon_no=recon_no,
            diff_id=str(diff_id),
            handle_action=handle_action,
        )
        return handled

    async def complete_reconciliation(
        self, tenant_id: UUID, recon_no: str
    ) -> ReconciliationAggregate:
        recon = await self._recon_repo.get_by_no(recon_no)
        if recon is None:
            raise FINError(
                FINErrorCode.RECON_NOT_FOUND,
                f"reconciliation {recon_no} not found",
            )
        completed = recon.complete()
        await self._recon_repo.save(completed)
        logger.info("recon_completed", recon_no=recon_no)
        return completed

    async def get_recon_report(
        self, tenant_id: UUID, recon_no: str
    ) -> dict[str, Any]:
        recon = await self._recon_repo.get_by_no(recon_no)
        if recon is None:
            raise FINError(
                FINErrorCode.RECON_NOT_FOUND,
                f"reconciliation {recon_no} not found",
            )
        return {
            "recon_no": recon.recon_no,
            "period_start": recon.period_start.isoformat(),
            "period_end": recon.period_end.isoformat(),
            "scope_type": recon.scope_type,
            "scope_value": recon.scope_value,
            "data_source": recon.data_source,
            "status": recon.status.value,
            "system_amount": str(recon.system_amount.amount),
            "external_amount": str(recon.external_amount.amount),
            "matched_count": recon.matched_count,
            "diff_count": recon.diff_count,
            "differences": [
                {
                    "diff_id": str(d.diff_id),
                    "business_ref_type": d.business_ref_type,
                    "business_ref_id": d.business_ref_id,
                    "diff_type": d.diff_type.value,
                    "diff_amount": str(d.diff_amount.amount),
                    "handle_status": d.handle_status.value,
                }
                for d in recon.differences
            ],
            "handle_records": [
                {
                    "record_id": str(r.record_id),
                    "diff_id": str(r.diff_id),
                    "handle_action": r.handle_action,
                    "handler_id": r.handler_id,
                    "handled_at": r.handled_at.isoformat(),
                }
                for r in recon.handle_records
            ],
        }