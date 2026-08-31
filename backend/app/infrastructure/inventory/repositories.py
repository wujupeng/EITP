"""INV 仓储实现 - 商品、库存余额、账本、事务、单据。"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.aggregates.inventory_balance_aggregate import InventoryBalanceAggregate
from app.domain.inventory.aggregates.inventory_ledger_aggregate import InventoryLedgerAggregate
from app.domain.inventory.aggregates.inventory_transaction_aggregate import (
    InventoryTransactionAggregate,
)
from app.domain.inventory.value_objects.shared import TransactionStatus, TransactionType
from app.domain.product.aggregates.product_aggregate import ProductAggregate, Sku
from app.domain.shared.entity import EntityId
from app.infrastructure.inventory.models import (
    DocumentORM,
    InventoryBalanceORM,
    InventoryLedgerORM,
    InventoryTransactionORM,
    ProductORM,
    SkuORM,
)


class ProductRepository:
    """商品仓储。"""

    async def create(self, session: AsyncSession, product: ProductAggregate) -> ProductORM:
        orm = ProductORM(
            id=product.id.value,
            tenant_id=product.tenant_id,
            product_code=product.product_code,
            product_name=product.product_name,
            category_id=product.category_id,
            brand_id=product.brand_id,
            base_unit_id=product.base_unit_id,
            description=product.description,
            status=product.status.value,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, product_id: UUID) -> ProductORM | None:
        stmt = select(ProductORM).where(
            ProductORM.tenant_id == tenant_id,
            ProductORM.id == product_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, session: AsyncSession, tenant_id: UUID, code: str) -> ProductORM | None:
        stmt = select(ProductORM).where(
            ProductORM.tenant_id == tenant_id,
            ProductORM.product_code == code,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID, limit: int = 100, offset: int = 0) -> list[ProductORM]:
        stmt = select(ProductORM).where(
            ProductORM.tenant_id == tenant_id,
        ).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())


class SkuRepository:
    """SKU 仓储。"""

    async def create(self, session: AsyncSession, sku: Sku) -> SkuORM:
        import json
        orm = SkuORM(
            id=sku.sku_id.value,
            tenant_id=sku.tenant_id,
            product_id=sku.product_id.value,
            sku_code=sku.sku_code,
            sku_name=sku.sku_name,
            specification=json.dumps(sku.specification) if sku.specification else None,
            barcode_list=json.dumps(sku.barcode_list) if sku.barcode_list else None,
            unit_id=sku.unit_id,
            weight=sku.weight,
            volume=sku.volume,
            status=sku.status.value,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_code(self, session: AsyncSession, tenant_id: UUID, code: str) -> SkuORM | None:
        stmt = select(SkuORM).where(
            SkuORM.tenant_id == tenant_id,
            SkuORM.sku_code == code,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class InventoryBalanceRepository:
    """库存余额仓储。"""

    async def get_or_create(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        location_id: UUID | None = None,
        batch_no: str | None = None,
    ) -> InventoryBalanceAggregate:
        stmt = select(InventoryBalanceORM).where(
            InventoryBalanceORM.tenant_id == tenant_id,
            InventoryBalanceORM.sku_id == sku_id,
            InventoryBalanceORM.warehouse_id == warehouse_id,
        )
        result = await session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            orm = InventoryBalanceORM(
                id=uuid4(),
                tenant_id=tenant_id,
                sku_id=sku_id,
                warehouse_id=warehouse_id,
                location_id=location_id,
                batch_no=batch_no,
            )
            session.add(orm)
            await session.flush()

        return InventoryBalanceAggregate(
            id=EntityId(orm.id),
            tenant_id=orm.tenant_id,
            sku_id=orm.sku_id,
            warehouse_id=orm.warehouse_id,
            location_id=orm.location_id,
            batch_no=orm.batch_no,
            on_hand=orm.on_hand,
            reserved=orm.reserved,
            in_transit=orm.in_transit,
            inspection=orm.inspection,
            blocked=orm.blocked,
            unit_cost=orm.unit_cost,
            last_ledger_id=orm.last_ledger_id,
        )

    async def save(self, session: AsyncSession, balance: InventoryBalanceAggregate) -> None:
        stmt = select(InventoryBalanceORM).where(InventoryBalanceORM.id == balance.id.value)
        result = await session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            orm = InventoryBalanceORM(
                id=balance.id.value,
                tenant_id=balance.tenant_id,
                sku_id=balance.sku_id,
                warehouse_id=balance.warehouse_id,
            )
            session.add(orm)
        orm.on_hand = balance.on_hand
        orm.reserved = balance.reserved
        orm.in_transit = balance.in_transit
        orm.inspection = balance.inspection
        orm.blocked = balance.blocked
        orm.unit_cost = balance.unit_cost
        orm.last_ledger_id = balance.last_ledger_id
        await session.flush()

    async def query(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID | None = None,
        warehouse_id: UUID | None = None,
    ) -> list[InventoryBalanceORM]:
        stmt = select(InventoryBalanceORM).where(InventoryBalanceORM.tenant_id == tenant_id)
        if sku_id is not None:
            stmt = stmt.where(InventoryBalanceORM.sku_id == sku_id)
        if warehouse_id is not None:
            stmt = stmt.where(InventoryBalanceORM.warehouse_id == warehouse_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())


class InventoryLedgerRepository:
    """库存账本仓储 - append-only。"""

    async def append(self, session: AsyncSession, ledger: InventoryLedgerAggregate) -> InventoryLedgerORM:
        orm = InventoryLedgerORM(
            id=ledger.id.value,
            transaction_id=ledger.transaction_id,
            correlation_id=ledger.correlation_id,
            document_id=ledger.document_id,
            document_type=ledger.document_type,
            idempotency_key=ledger.idempotency_key,
            tenant_id=ledger.tenant_id,
            organization_id=ledger.organization_id,
            site_id=ledger.site_id,
            warehouse_id=ledger.warehouse_id,
            location_id=ledger.location_id,
            sku_id=ledger.sku_id,
            transaction_type=ledger.transaction_type.value,
            direction=ledger.direction.value,
            quantity_before=ledger.quantity_before,
            quantity_change=ledger.quantity_change,
            quantity_after=ledger.quantity_after,
            unit_cost=ledger.unit_cost,
            total_cost=ledger.total_cost,
            reason=ledger.reason,
            operated_by=ledger.operated_by,
            operated_at=ledger.operated_at,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def list_by_sku_warehouse(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        limit: int = 100,
    ) -> list[InventoryLedgerORM]:
        stmt = select(InventoryLedgerORM).where(
            InventoryLedgerORM.tenant_id == tenant_id,
            InventoryLedgerORM.sku_id == sku_id,
            InventoryLedgerORM.warehouse_id == warehouse_id,
        ).order_by(InventoryLedgerORM.operated_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())


class InventoryTransactionRepository:
    """库存事务仓储。"""

    async def create(self, session: AsyncSession, tx: InventoryTransactionAggregate) -> InventoryTransactionORM:
        orm = InventoryTransactionORM(
            id=tx.id.value,
            tenant_id=tx.tenant_id,
            sku_id=tx.sku_id,
            warehouse_id=tx.warehouse_id,
            location_id=tx.location_id,
            organization_id=tx.organization_id,
            site_id=tx.site_id,
            transaction_type=tx.transaction_type.value,
            quantity=tx.quantity,
            idempotency_key=tx.idempotency_key,
            correlation_id=tx.correlation_id,
            document_id=tx.document_id,
            document_type=tx.document_type,
            status=tx.status.value,
            result_ledger_id=tx.result_ledger_id,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def update_status(self, session: AsyncSession, tx_id: UUID, status: str, ledger_id: UUID | None = None) -> None:
        stmt = select(InventoryTransactionORM).where(InventoryTransactionORM.id == tx_id)
        result = await session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is not None:
            orm.status = status
            if ledger_id is not None:
                orm.result_ledger_id = ledger_id
            await session.flush()


class DocumentRepository:
    """单据仓储。"""

    async def create(self, session: AsyncSession, doc_orm: DocumentORM) -> DocumentORM:
        session.add(doc_orm)
        await session.flush()
        return doc_orm

    async def get_by_id(self, session: AsyncSession, tenant_id: UUID, doc_id: UUID) -> DocumentORM | None:
        stmt = select(DocumentORM).where(
            DocumentORM.tenant_id == tenant_id,
            DocumentORM.id == doc_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID, limit: int = 100, offset: int = 0) -> list[DocumentORM]:
        stmt = select(DocumentORM).where(
            DocumentORM.tenant_id == tenant_id,
        ).order_by(DocumentORM.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())