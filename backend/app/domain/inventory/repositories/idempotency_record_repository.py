"""幂等记录仓储 Protocol - Redis + DB 两级存储。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class IdempotencyRecord:
    tenant_id: UUID
    idempotency_key: str
    transaction_id: UUID
    result: dict
    request_hash: str


class IdempotencyRecordRepository(Protocol):
    """幂等记录仓储协议。"""

    async def get(self, tenant_id: UUID, key: str) -> IdempotencyRecord | None:
        ...

    async def save(self, record: IdempotencyRecord) -> None:
        ...

    @staticmethod
    def compute_request_hash(request: dict) -> str:
        ...