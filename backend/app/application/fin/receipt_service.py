"""FIN 收款应用服务 - ReceiptService。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.fin.aggregates.collection_task_aggregate import (
    CollectionTaskAggregate,
)
from app.domain.fin.aggregates.receipt_aggregate import (
    ReceiptAggregate,
    WriteOffLine,
)
from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import CollectionStage
from app.domain.fin.value_objects.money import Money
from app.infrastructure.fin.ar_voucher_repository import ARVoucherRepository
from app.infrastructure.fin.collection_task_repository import CollectionTaskRepository
from app.infrastructure.fin.receipt_repository import ReceiptRepository

logger = get_logger(__name__)


class ReceiptService:
    """收款应用服务 - 确认收款/核销/催收处理。"""

    def __init__(
        self,
        receipt_repo: ReceiptRepository,
        ar_repo: ARVoucherRepository,
        collection_task_repo: CollectionTaskRepository,
    ) -> None:
        self._receipt_repo = receipt_repo
        self._ar_repo = ar_repo
        self._collection_task_repo = collection_task_repo

    async def confirm_receipt(
        self,
        tenant_id: UUID,
        receipt_no: str,
    ) -> ReceiptAggregate:
        receipt = await self._receipt_repo.get_by_no(receipt_no)
        if receipt is None:
            raise FINError(
                FINErrorCode.RECEIPT_NOT_FOUND,
                f"receipt {receipt_no} not found",
            )
        confirmed = receipt.confirm()
        await self._receipt_repo.save(confirmed)
        logger.info("receipt_confirmed", receipt_no=receipt_no)
        return confirmed

    async def write_off_receipt(
        self,
        tenant_id: UUID,
        receipt_no: str,
        write_off_lines: list[dict[str, Any]],
    ) -> ReceiptAggregate:
        receipt = await self._receipt_repo.get_by_no(receipt_no)
        if receipt is None:
            raise FINError(
                FINErrorCode.RECEIPT_NOT_FOUND,
                f"receipt {receipt_no} not found",
            )
        if receipt.status.value == "WRITE_OFF":
            raise FINError(
                FINErrorCode.RECEIPT_ALREADY_WRITEOFF,
                f"receipt {receipt_no} already write-off",
            )
        currency = receipt.receipt_amount.currency
        domain_lines: list[WriteOffLine] = []
        for idx, ln in enumerate(write_off_lines, start=1):
            domain_lines.append(
                WriteOffLine(
                    line_no=ln.get("line_no", idx),
                    ar_voucher_no=ln["ar_voucher_no"],
                    write_off_amount=Money(
                        Decimal(str(ln["write_off_amount"])), currency
                    ),
                )
            )
        written_off = receipt.write_off(domain_lines)
        await self._receipt_repo.save(written_off)
        for ln in domain_lines:
            ar_voucher = await self._ar_repo.get_by_no(ln.ar_voucher_no)
            if ar_voucher is not None:
                updated_ar = ar_voucher.apply_receipt(ln.write_off_amount)
                await self._ar_repo.save(updated_ar)
        logger.info("receipt_write_off", receipt_no=receipt_no)
        return written_off

    async def handle_collection_task(
        self,
        tenant_id: UUID,
        task_id: UUID,
        handler_id: str,
        content: str,
        stage: str | None = None,
    ) -> CollectionTaskAggregate:
        task = await self._collection_task_repo.get_by_id(task_id)
        if task is None:
            raise FINError(
                FINErrorCode.COLLECTION_TASK_NOT_FOUND,
                f"collection task {task_id} not found",
            )
        domain_stage = CollectionStage(stage) if stage else None
        handled = task.handle(handler_id, content, domain_stage)
        await self._collection_task_repo.save(handled)
        logger.info(
            "collection_task_handled",
            task_id=str(task_id),
            handler_id=handler_id,
        )
        return handled

    async def escalate_collection_task(
        self,
        tenant_id: UUID,
        task_id: UUID,
        handler_id: str,
        content: str,
    ) -> CollectionTaskAggregate:
        task = await self._collection_task_repo.get_by_id(task_id)
        if task is None:
            raise FINError(
                FINErrorCode.COLLECTION_TASK_NOT_FOUND,
                f"collection task {task_id} not found",
            )
        escalated = task.escalate(handler_id, content)
        await self._collection_task_repo.save(escalated)
        logger.info("collection_task_escalated", task_id=str(task_id))
        return escalated

    async def resolve_collection_task(
        self,
        tenant_id: UUID,
        task_id: UUID,
        handler_id: str,
        content: str,
    ) -> CollectionTaskAggregate:
        task = await self._collection_task_repo.get_by_id(task_id)
        if task is None:
            raise FINError(
                FINErrorCode.COLLECTION_TASK_NOT_FOUND,
                f"collection task {task_id} not found",
            )
        resolved = task.resolve(handler_id, content)
        await self._collection_task_repo.save(resolved)
        logger.info("collection_task_resolved", task_id=str(task_id))
        return resolved