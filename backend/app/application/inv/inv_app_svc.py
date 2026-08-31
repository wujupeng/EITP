"""INV 应用服务 - 商品管理、库存事务、库存查询、单据管理。"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.aggregates.inventory_transaction_aggregate import (
    InventoryTransactionAggregate,
)
from app.domain.inventory.services.inventory_audit_writer import InventoryAuditWriter
from app.domain.inventory.services.inventory_transaction_executor import (
    InventoryTransactionExecutor,
)
from app.domain.inventory.value_objects.shared import TransactionType
from app.domain.shared.entity import EntityId
from app.infrastructure.inventory.repositories import (
    DocumentRepository,
    InventoryBalanceRepository,
    InventoryLedgerRepository,
    InventoryTransactionRepository,
    ProductRepository,
    SkuRepository,
)
from app.interfaces.middleware.error_handler import INVError, INVErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class ProductAppSvc:
    """商品管理应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._product_repo = ProductRepository()
        self._sku_repo = SkuRepository()

    async def create_product(self, tenant_id: UUID, code: str, name: str, **kwargs) -> dict:
        existing = await self._product_repo.get_by_code(self._session, tenant_id, code)
        if existing is not None:
            raise INVError(INVErrorCode.PRODUCT_DUPLICATE, f"商品编码 {code} 已存在")
        from app.domain.product.aggregates.product_aggregate import ProductAggregate
        product = ProductAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            product_code=code,
            product_name=name,
            category_id=kwargs.get("category_id"),
            brand_id=kwargs.get("brand_id"),
            base_unit_id=kwargs.get("base_unit_id"),
            description=kwargs.get("description"),
        )
        orm = await self._product_repo.create(self._session, product)
        await self._session.commit()
        return {
            "id": str(orm.id),
            "product_code": orm.product_code,
            "product_name": orm.product_name,
            "status": orm.status,
        }

    async def list_products(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> list[dict]:
        products = await self._product_repo.list_by_tenant(self._session, tenant_id, limit, offset)
        return [
            {
                "id": str(p.id),
                "product_code": p.product_code,
                "product_name": p.product_name,
                "status": p.status,
            }
            for p in products
        ]


class InventoryAppSvc:
    """库存事务应用服务 - 核心编排器。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._balance_repo = InventoryBalanceRepository()
        self._ledger_repo = InventoryLedgerRepository()
        self._tx_repo = InventoryTransactionRepository()
        self._executor = InventoryTransactionExecutor()
        self._audit_writer = InventoryAuditWriter()

    async def execute_transaction(
        self,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        transaction_type: str,
        quantity: float,
        idempotency_key: str,
        operated_by: UUID,
        **kwargs,
    ) -> dict:
        tx_type = TransactionType(transaction_type)
        tx = InventoryTransactionAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            transaction_type=tx_type,
            quantity=quantity,
            idempotency_key=idempotency_key,
            correlation_id=kwargs.get("correlation_id"),
            document_id=kwargs.get("document_id"),
            document_type=kwargs.get("document_type"),
            organization_id=kwargs.get("organization_id"),
            site_id=kwargs.get("site_id"),
            location_id=kwargs.get("location_id"),
        )

        balance = await self._balance_repo.get_or_create(
            self._session, tenant_id, sku_id, warehouse_id,
            kwargs.get("location_id"),
        )

        tx_orm = await self._tx_repo.create(self._session, tx)

        tx = await self._executor.execute(
            session=self._session,
            transaction=tx,
            balance=balance,
            operated_by=operated_by,
            unit_cost=kwargs.get("unit_cost"),
            reason=kwargs.get("reason"),
        )

        await self._balance_repo.save(self._session, balance)
        await self._tx_repo.update_status(
            self._session, tx.id.value, tx.status.value,
            tx.result_ledger_id,
        )
        await self._session.commit()

        return {
            "id": str(tx.id.value),
            "transaction_type": tx.transaction_type.value,
            "quantity": tx.quantity,
            "status": tx.status.value,
            "result_ledger_id": str(tx.result_ledger_id) if tx.result_ledger_id else None,
        }

    async def query_balance(
        self,
        tenant_id: UUID,
        sku_id: UUID | None = None,
        warehouse_id: UUID | None = None,
    ) -> list[dict]:
        balances = await self._balance_repo.query(self._session, tenant_id, sku_id, warehouse_id)
        return [
            {
                "id": str(b.id),
                "sku_id": str(b.sku_id),
                "warehouse_id": str(b.warehouse_id),
                "on_hand": b.on_hand,
                "reserved": b.reserved,
                "available": b.on_hand - b.reserved,
                "in_transit": b.in_transit,
                "inspection": b.inspection,
                "blocked": b.blocked,
                "unit_cost": b.unit_cost,
            }
            for b in balances
        ]

    async def query_ledger(
        self,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        limit: int = 100,
    ) -> list[dict]:
        ledgers = await self._ledger_repo.list_by_sku_warehouse(
            self._session, tenant_id, sku_id, warehouse_id, limit,
        )
        return [
            {
                "id": str(l.id),
                "transaction_id": str(l.transaction_id),
                "transaction_type": l.transaction_type,
                "direction": l.direction,
                "quantity_before": l.quantity_before,
                "quantity_change": l.quantity_change,
                "quantity_after": l.quantity_after,
                "operated_at": l.operated_at.isoformat(),
            }
            for l in ledgers
        ]


class DocumentAppSvc:
    """单据管理应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._doc_repo = DocumentRepository()

    async def list_documents(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> list[dict]:
        docs = await self._doc_repo.list_by_tenant(self._session, tenant_id, limit, offset)
        return [
            {
                "id": str(d.id),
                "document_type": d.document_type,
                "document_number": d.document_number,
                "status": d.status,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ]