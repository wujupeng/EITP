"""幂等记录聚合根 - 全平台统一幂等键格式。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

IDEMPOTENCY_KEY_PREFIX = "eitp"
IDEMPOTENCY_KEY_SEGMENT = "idem"


def build_idempotency_key(tenant_id: UUID | str, key: str) -> str:
    """构造全平台统一幂等键格式: eitp:{tenant_id}:idem:{key}"""
    return f"{IDEMPOTENCY_KEY_PREFIX}:{tenant_id}:{IDEMPOTENCY_KEY_SEGMENT}:{key}"


def compute_request_hash(body: bytes) -> str:
    """计算请求体 SHA-256 哈希。"""
    return hashlib.sha256(body).hexdigest()


@dataclass(frozen=True)
class IdempotencyRecordAggregate:
    """幂等记录聚合根 - 防重复提交。"""

    idempotency_key: str
    tenant_id: UUID
    request_hash: str
    response_cache: dict
    response_status: int
    trace_id: str
    created_at: datetime
    expires_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        key: str,
        request_hash: str,
        response_cache: dict,
        response_status: int,
        trace_id: str,
        ttl_seconds: int = 86400,
    ) -> IdempotencyRecordAggregate:
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        return cls(
            idempotency_key=build_idempotency_key(tenant_id, key),
            tenant_id=tenant_id,
            request_hash=request_hash,
            response_cache=response_cache,
            response_status=response_status,
            trace_id=trace_id,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        check_time = now or datetime.now(timezone.utc)
        return check_time > self.expires_at

    def matches_request(self, request_hash: str) -> bool:
        return self.request_hash == request_hash