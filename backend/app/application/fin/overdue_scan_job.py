"""FIN 逾期扫描作业 - OverdueScanJob。"""

from __future__ import annotations

from datetime import date, timezone
from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.fin.aggregates.collection_task_aggregate import (
    CollectionTaskAggregate,
)
from app.domain.fin.value_objects.money import Money
from app.infrastructure.fin.ar_voucher_repository import ARVoucherRepository
from app.infrastructure.fin.collection_task_repository import CollectionTaskRepository

logger = get_logger(__name__)


class OverdueScanJob:
    """逾期扫描作业 - 扫描逾期 AR 凭证并生成/更新催收任务。"""

    def __init__(
        self,
        ar_repo: ARVoucherRepository,
        collection_task_repo: CollectionTaskRepository,
    ) -> None:
        self._ar_repo = ar_repo
        self._collection_task_repo = collection_task_repo

    async def scan(self, tenant_id: UUID, as_of_date: date | None = None) -> dict[str, Any]:
        ref_date = as_of_date or date.today()
        ar_vouchers = await self._ar_repo.list_ar_vouchers(
            tenant_id, is_overdue=True, limit=100000, offset=0
        )
        created_count = 0
        updated_count = 0
        for v in ar_vouchers:
            if v.due_date is None:
                continue
            overdue_days = (ref_date - v.due_date).days
            if overdue_days <= 0:
                continue
            existing_task = await self._collection_task_repo.get_by_ar_voucher_no(
                v.voucher_no
            )
            if existing_task is None:
                task = CollectionTaskAggregate.create(
                    ar_voucher_no=v.voucher_no,
                    overdue_amount=v.unreceived_amount,
                    overdue_days=overdue_days,
                    tenant_id=tenant_id,
                )
                await self._collection_task_repo.save(task)
                created_count += 1
            else:
                from dataclasses import replace as dataclass_replace
                from datetime import datetime
                updated = dataclass_replace(
                    existing_task,
                    overdue_amount=v.unreceived_amount,
                    overdue_days=overdue_days,
                    updated_at=datetime.now(timezone),
                )
                await self._collection_task_repo.save(updated)
                updated_count += 1
        logger.info(
            "overdue_scan_completed",
            tenant_id=str(tenant_id),
            created=created_count,
            updated=updated_count,
        )
        return {
            "tenant_id": str(tenant_id),
            "as_of_date": ref_date.isoformat(),
            "created": created_count,
            "updated": updated_count,
            "total_scanned": len(ar_vouchers),
        }