"""幂等记录 Redis 缓存 - 短时去重，TTL=7 天。"""

from __future__ import annotations

import json
from uuid import UUID

from app.infrastructure.cache.redis_client import (
    IDEMPOTENCY_TTL,
    get_redis,
    idempotency_key,
)
from app.domain.inventory.repositories.idempotency_record_repository import (
    IdempotencyRecord,
)


class IdempotencyRedisStore:
    """幂等记录 Redis 缓存。"""

    async def get(self, tenant_id: UUID, key: str) -> IdempotencyRecord | None:
        try:
            r = await get_redis()
            data = await r.get(idempotency_key(str(tenant_id), key))
            if data is None:
                return None
            d = json.loads(data)
            return IdempotencyRecord(
                tenant_id=UUID(d["tenant_id"]),
                idempotency_key=d["idempotency_key"],
                transaction_id=UUID(d["transaction_id"]),
                result=d["result"],
                request_hash=d["request_hash"],
            )
        except Exception:
            return None

    async def set(self, tenant_id: UUID, key: str, record: IdempotencyRecord) -> None:
        try:
            r = await get_redis()
            data = json.dumps({
                "tenant_id": str(record.tenant_id),
                "idempotency_key": record.idempotency_key,
                "transaction_id": str(record.transaction_id),
                "result": record.result,
                "request_hash": record.request_hash,
            })
            await r.set(
                idempotency_key(str(tenant_id), key),
                data,
                ex=IDEMPOTENCY_TTL,
            )
        except Exception:
            pass