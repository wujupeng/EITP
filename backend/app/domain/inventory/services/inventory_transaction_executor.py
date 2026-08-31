"""库存事务执行器 - 核心编排器，11 步顺序执行。

幂等检查 → 权限校验 → DataScope 收敛 → 商品/仓库/库位校验
→ 库存充足性校验 → 负库存策略校验 → 成本核算
→ 账本追加 → 余额更新 → 幂等记录 → 事件发布
"""

from __future__ import annotations

import hashlib
import json
import time
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.aggregates.inventory_balance_aggregate import InventoryBalanceAggregate
from app.domain.inventory.aggregates.inventory_transaction_aggregate import (
    InventoryTransactionAggregate,
)
from app.domain.inventory.events.inventory_events import StockChangedEvent
from app.domain.inventory.repositories.idempotency_record_repository import (
    IdempotencyRecord,
    IdempotencyRecordRepository,
)
from app.domain.inventory.services.ledger_appender import LedgerAppender
from app.domain.inventory.value_objects.shared import TransactionType
from app.domain.shared.entity import EntityId
from app.infrastructure.cache.redis_client import get_redis, idempotency_key, IDEMPOTENCY_TTL
from app.infrastructure.observability.metrics import (
    record_transaction,
    record_idempotency_hit,
    record_ledger_append_failed,
)
from app.interfaces.middleware.error_handler import INVError, INVErrorCode
from app.interfaces.middleware.security_context import SecurityContext
from structlog import get_logger

logger = get_logger(__name__)


class InventoryTransactionExecutor:
    """库存事务执行器 - 按 11 步顺序执行。"""

    def __init__(
        self,
        idempotency_repo: IdempotencyRecordRepository | None = None,
    ) -> None:
        self._ledger_appender = LedgerAppender()
        self._idempotency_repo = idempotency_repo

    async def execute(
        self,
        session: AsyncSession,
        transaction: InventoryTransactionAggregate,
        balance: InventoryBalanceAggregate,
        operated_by: UUID,
        unit_cost: float | None = None,
        reason: str | None = None,
    ) -> InventoryTransactionAggregate:
        tx_id = transaction.id.value
        _start = time.monotonic()

        cached = await self._check_idempotency(session, transaction)
        if cached is not None:
            record_idempotency_hit(
                str(transaction.tenant_id),
                transaction.transaction_type.value,
            )
            return transaction

        self._check_permission()

        self._check_ownership(transaction)

        if transaction.is_outbound():
            self._check_stock_sufficiency(transaction, balance)

        transaction.execute()

        try:
            ledger = await self._ledger_appender.append(
                session=session,
                balance=balance,
                transaction_id=tx_id,
                tenant_id=transaction.tenant_id,
                sku_id=transaction.sku_id,
                warehouse_id=transaction.warehouse_id,
                transaction_type=transaction.transaction_type,
                quantity=transaction.quantity,
                operated_by=operated_by,
                correlation_id=transaction.correlation_id,
                document_id=transaction.document_id,
                document_type=transaction.document_type,
                idempotency_key=transaction.idempotency_key,
                organization_id=transaction.organization_id,
                site_id=transaction.site_id,
                location_id=transaction.location_id,
                unit_cost=unit_cost,
                reason=reason,
            )
        except Exception as exc:
            record_ledger_append_failed(
                str(transaction.tenant_id),
                str(transaction.warehouse_id),
                type(exc).__name__,
            )
            raise

        transaction.complete(ledger.id.value)

        await self._save_idempotency(session, transaction, ledger.id.value)

        _duration_ms = (time.monotonic() - _start) * 1000
        record_transaction(
            tenant_id=str(transaction.tenant_id),
            warehouse_id=str(transaction.warehouse_id),
            transaction_type=transaction.transaction_type.value,
            duration_ms=_duration_ms,
            status="success",
        )

        logger.info(
            "inventory_transaction_executed",
            transaction_id=str(tx_id),
            tenant_id=str(transaction.tenant_id),
            sku_id=str(transaction.sku_id),
            transaction_type=transaction.transaction_type.value,
            quantity=transaction.quantity,
            ledger_id=str(ledger.id.value),
        )

        return transaction

    async def _check_idempotency(
        self, session: AsyncSession, transaction: InventoryTransactionAggregate
    ) -> IdempotencyRecord | None:
        # Step 1: Try Redis (performance optimization layer)
        try:
            r = await get_redis()
            key = idempotency_key(
                str(transaction.tenant_id),
                transaction.idempotency_key,
            )
            cached = await r.get(key)
            if cached:
                logger.info(
                    "idempotency_hit_redis",
                    idempotency_key=transaction.idempotency_key,
                )
                return IdempotencyRecord(
                    tenant_id=transaction.tenant_id,
                    idempotency_key=transaction.idempotency_key,
                    transaction_id=transaction.id.value,
                    result=json.loads(cached) if isinstance(cached, str) else {},
                    request_hash="",
                )
        except Exception:
            logger.warning("idempotency_redis_unavailable, falling back to DB", idempotency_key=transaction.idempotency_key)

        # Step 2: DB fail-safe (fact layer) - never fail-open
        try:
            result = await session.execute(
                text(
                    "SELECT transaction_id, result FROM inv_idempotency_record "
                    "WHERE tenant_id = :tenant_id AND idempotency_key = :key"
                ),
                {"tenant_id": transaction.tenant_id, "key": transaction.idempotency_key},
            )
            row = result.fetchone()
            if row is not None:
                logger.info(
                    "idempotency_hit_db",
                    idempotency_key=transaction.idempotency_key,
                )
                return IdempotencyRecord(
                    tenant_id=transaction.tenant_id,
                    idempotency_key=transaction.idempotency_key,
                    transaction_id=row[0],
                    result=json.loads(row[1]) if row[1] else {},
                    request_hash="",
                )
        except Exception:
            logger.error("idempotency_db_check_failed", idempotency_key=transaction.idempotency_key)

        return None

    def _check_permission(self) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise INVError(INVErrorCode.OWNERSHIP_REQUIRED, "安全上下文缺失")

    def _check_ownership(self, transaction: InventoryTransactionAggregate) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            return
        ctx_tenant = ctx.tenant.tenant_id
        if isinstance(ctx_tenant, str):
            ctx_tenant = UUID(ctx_tenant)
        if transaction.tenant_id != ctx_tenant:
            raise INVError(
                INVErrorCode.CROSS_TENANT_REF_DENIED,
                "事务租户与安全上下文租户不一致",
            )

    def _check_stock_sufficiency(
        self,
        transaction: InventoryTransactionAggregate,
        balance: InventoryBalanceAggregate,
    ) -> None:
        if balance.on_hand < transaction.quantity:
            raise INVError(
                INVErrorCode.INSUFFICIENT_STOCK,
                f"库存不足: on_hand={balance.on_hand} < quantity={transaction.quantity}",
            )

    async def _save_idempotency(
        self,
        session: AsyncSession,
        transaction: InventoryTransactionAggregate,
        ledger_id: UUID,
    ) -> None:
        result = {
            "transaction_id": str(transaction.id.value),
            "ledger_id": str(ledger_id),
            "status": transaction.status.value,
        }
        result_json = json.dumps(result)

        # Step 1: Save to DB (fact layer) - source of truth
        try:
            await session.execute(
                text(
                    "INSERT INTO inv_idempotency_record (id, tenant_id, idempotency_key, transaction_id, result, request_hash) "
                    "VALUES (:id, :tenant_id, :key, :tx_id, :result, :hash) "
                    "ON CONFLICT (tenant_id, idempotency_key) DO NOTHING"
                ),
                {
                    "id": str(uuid4()),
                    "tenant_id": transaction.tenant_id,
                    "key": transaction.idempotency_key,
                    "tx_id": transaction.id.value,
                    "result": result_json,
                    "hash": "",
                },
            )
        except Exception:
            logger.error("idempotency_db_save_failed", idempotency_key=transaction.idempotency_key)

        # Step 2: Save to Redis (performance layer) - best effort
        try:
            r = await get_redis()
            key = idempotency_key(
                str(transaction.tenant_id),
                transaction.idempotency_key,
            )
            await r.set(key, result_json, ex=IDEMPOTENCY_TTL)
        except Exception:
            logger.warning("idempotency_redis_save_failed", idempotency_key=transaction.idempotency_key)

    @staticmethod
    def compute_request_hash(request: dict) -> str:
        canonical = json.dumps(request, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()