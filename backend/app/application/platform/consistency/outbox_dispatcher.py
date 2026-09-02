"""Outbox 投递器 - 至少一次投递保证。"""

from __future__ import annotations

import asyncio
from typing import Any, Callable
from uuid import UUID

from structlog import get_logger

from app.domain.platform.consistency.aggregates.outbox_event_aggregate import (
    DeliveryStatus,
    OutboxEventAggregate,
)
from app.domain.platform.error_codes import PLTErrorCode
from app.domain.platform.exceptions import PLTError

logger = get_logger(__name__)


class OutboxDispatcher:
    """Outbox 投递器 - 轮询未投递事件，保证至少一次投递。"""

    def __init__(
        self,
        repository: Any,
        delivery_handler: Callable | None = None,
        poll_interval: float = 1.0,
        batch_size: int = 100,
    ) -> None:
        self._repository = repository
        self._delivery_handler = delivery_handler
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("outbox_dispatcher_started")
        while self._running:
            try:
                await self._dispatch_batch()
            except Exception as exc:
                logger.error("outbox_dispatch_error", error=str(exc))
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("outbox_dispatcher_stopped")

    async def _dispatch_batch(self) -> int:
        events = await self._repository.get_pending_events(limit=self._batch_size)
        if not events:
            return 0

        delivered = 0
        for event_data in events:
            try:
                if self._delivery_handler is not None:
                    await self._delivery_handler(event_data)
                await self._repository.mark_delivered(event_data["event_id"])
                delivered += 1
                logger.debug("outbox_delivered", event_id=str(event_data["event_id"]))
            except Exception as exc:
                await self._repository.increment_attempts(event_data["event_id"])
                logger.warning(
                    "outbox_delivery_failed",
                    event_id=str(event_data["event_id"]),
                    error=str(exc),
                )
        return delivered

    async def retry_dead_letters(self, max_count: int = 100) -> int:
        events = await self._repository.get_dead_letter_events(limit=max_count)
        retried = 0
        for event_data in events:
            try:
                if self._delivery_handler is not None:
                    await self._delivery_handler(event_data)
                await self._repository.mark_delivered(event_data["event_id"])
                retried += 1
            except Exception as exc:
                logger.error("outbox_retry_failed", event_id=str(event_data["event_id"]), error=str(exc))
        return retried