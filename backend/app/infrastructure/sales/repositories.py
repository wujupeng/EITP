"""SAL 仓储实现 - 客户/报价/订单/发货/包装/退货/结算/发票/收款/审计。

企业级表含 tenant_id，查询自动过滤租户。复用 MT-001 TenantFilterEvent 模式。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.sales.models import (
    SalCreditLimitORM, SalCustomerAddressORM, SalCustomerCategoryORM,
    SalCustomerContactORM, SalCustomerORM, SalCustomerPricingORM,
    SalInvoiceLineORM, SalSalesAuditORM, SalSalesInvoiceORM,
    SalSalesOrderLineORM, SalSalesOrderORM, SalSalesQuotationLineORM,
    SalSalesQuotationORM, SalSalesReturnORM, SalSalesSettlementORM,
    SalSettlementReconcileLineORM, SalPackingLineORM, SalPackingRecordORM,
    SalPaymentReceiptORM, SalReturnLineORM, SalShipmentLineORM,
    SalShipmentOrderORM,
)


# ────────────────────────────── 客户主数据仓储 ──────────────────────────────


class CustomerRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, cid: UUID) -> SalCustomerORM | None:
        return (await s.execute(select(SalCustomerORM).where(SalCustomerORM.tenant_id == tid, SalCustomerORM.customer_id == cid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> SalCustomerORM | None:
        return (await s.execute(select(SalCustomerORM).where(SalCustomerORM.tenant_id == tid, SalCustomerORM.customer_code == code))).scalar_one_or_none()

    async def list_by_tenant(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[SalCustomerORM]:
        return list((await s.execute(select(SalCustomerORM).where(SalCustomerORM.tenant_id == tid).offset(offset).limit(limit))).scalars().all())

    async def list_by_status(self, s: AsyncSession, tid: UUID, status: str, offset: int = 0, limit: int = 50) -> list[SalCustomerORM]:
        return list((await s.execute(select(SalCustomerORM).where(SalCustomerORM.tenant_id == tid, SalCustomerORM.status == status).offset(offset).limit(limit))).scalars().all())

    async def list_active_for_order(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[SalCustomerORM]:
        """仅 ACTIVE 状态客户可用于销售订单。"""
        return list((await s.execute(select(SalCustomerORM).where(SalCustomerORM.tenant_id == tid, SalCustomerORM.status == "active").offset(offset).limit(limit))).scalars().all())

    async def list_addresses(self, s: AsyncSession, tid: UUID, cid: UUID) -> list[SalCustomerAddressORM]:
        return list((await s.execute(select(SalCustomerAddressORM).where(SalCustomerAddressORM.tenant_id == tid, SalCustomerAddressORM.customer_id == cid))).scalars().all())

    async def list_contacts(self, s: AsyncSession, tid: UUID, cid: UUID) -> list[SalCustomerContactORM]:
        return list((await s.execute(select(SalCustomerContactORM).where(SalCustomerContactORM.tenant_id == tid, SalCustomerContactORM.customer_id == cid))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalCustomerORM) -> SalCustomerORM:
        s.add(orm); await s.flush(); return orm

    async def save_address(self, s: AsyncSession, orm: SalCustomerAddressORM) -> SalCustomerAddressORM:
        s.add(orm); await s.flush(); return orm

    async def save_contact(self, s: AsyncSession, orm: SalCustomerContactORM) -> SalCustomerContactORM:
        s.add(orm); await s.flush(); return orm


class CustomerCategoryRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, cid: UUID) -> SalCustomerCategoryORM | None:
        return (await s.execute(select(SalCustomerCategoryORM).where(SalCustomerCategoryORM.tenant_id == tid, SalCustomerCategoryORM.category_id == cid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> SalCustomerCategoryORM | None:
        return (await s.execute(select(SalCustomerCategoryORM).where(SalCustomerCategoryORM.tenant_id == tid, SalCustomerCategoryORM.category_code == code))).scalar_one_or_none()

    async def list_by_tenant(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[SalCustomerCategoryORM]:
        return list((await s.execute(select(SalCustomerCategoryORM).where(SalCustomerCategoryORM.tenant_id == tid).offset(offset).limit(limit))).scalars().all())

    async def list_active(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[SalCustomerCategoryORM]:
        return list((await s.execute(select(SalCustomerCategoryORM).where(SalCustomerCategoryORM.tenant_id == tid, SalCustomerCategoryORM.status == "active").offset(offset).limit(limit))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalCustomerCategoryORM) -> SalCustomerCategoryORM:
        s.add(orm); await s.flush(); return orm


class CreditLimitRepository:
    async def get_by_customer(self, s: AsyncSession, tid: UUID, cid: UUID) -> SalCreditLimitORM | None:
        return (await s.execute(select(SalCreditLimitORM).where(SalCreditLimitORM.tenant_id == tid, SalCreditLimitORM.customer_id == cid))).scalar_one_or_none()

    async def get_for_update(self, s: AsyncSession, tid: UUID, cid: UUID) -> SalCreditLimitORM | None:
        """悲观锁并发占用 - SELECT ... FOR UPDATE。"""
        return (await s.execute(select(SalCreditLimitORM).where(SalCreditLimitORM.tenant_id == tid, SalCreditLimitORM.customer_id == cid).with_for_update())).scalar_one_or_none()

    async def update_used_amount(self, s: AsyncSession, tid: UUID, cid: UUID, used_amount: float, version: int) -> None:
        """乐观锁版本号更新已用额度。"""
        await s.execute(update(SalCreditLimitORM).where(SalCreditLimitORM.tenant_id == tid, SalCreditLimitORM.customer_id == cid, SalCreditLimitORM.version == version).values(used_amount=used_amount, version=version + 1))

    async def list_by_tenant(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[SalCreditLimitORM]:
        return list((await s.execute(select(SalCreditLimitORM).where(SalCreditLimitORM.tenant_id == tid).offset(offset).limit(limit))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalCreditLimitORM) -> SalCreditLimitORM:
        s.add(orm); await s.flush(); return orm


class CustomerPricingRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, pid: UUID) -> SalCustomerPricingORM | None:
        return (await s.execute(select(SalCustomerPricingORM).where(SalCustomerPricingORM.tenant_id == tid, SalCustomerPricingORM.pricing_id == pid))).scalar_one_or_none()

    async def list_by_customer(self, s: AsyncSession, tid: UUID, cid: UUID) -> list[SalCustomerPricingORM]:
        return list((await s.execute(select(SalCustomerPricingORM).where(SalCustomerPricingORM.tenant_id == tid, SalCustomerPricingORM.customer_id == cid))).scalars().all())

    async def list_by_category(self, s: AsyncSession, tid: UUID, cat_id: UUID) -> list[SalCustomerPricingORM]:
        return list((await s.execute(select(SalCustomerPricingORM).where(SalCustomerPricingORM.tenant_id == tid, SalCustomerPricingORM.category_id == cat_id))).scalars().all())

    async def list_effective(self, s: AsyncSession, tid: UUID, now: datetime) -> list[SalCustomerPricingORM]:
        """查有效期内已发布价格。"""
        return list((await s.execute(select(SalCustomerPricingORM).where(SalCustomerPricingORM.tenant_id == tid, SalCustomerPricingORM.status == "published", SalCustomerPricingORM.valid_from <= now).order_by(SalCustomerPricingORM.priority.asc()))).scalars().all())

    async def match_by_priority(self, s: AsyncSession, tid: UUID, cid: UUID, cat_id: UUID | None, sku_id: UUID, now: datetime) -> SalCustomerPricingORM | None:
        """按优先级匹配：促销 1 > 协议 2 > 折扣 3 > 标准 4。"""
        q = select(SalCustomerPricingORM).where(
            SalCustomerPricingORM.tenant_id == tid,
            SalCustomerPricingORM.enterprise_sku_id == sku_id,
            SalCustomerPricingORM.status == "published",
            SalCustomerPricingORM.valid_from <= now,
        ).order_by(SalCustomerPricingORM.priority.asc())
        rows = list((await s.execute(q)).scalars().all())
        # 优先匹配客户专属价
        for r in rows:
            if r.customer_id == cid:
                return r
        # 其次匹配分类价
        if cat_id is not None:
            for r in rows:
                if r.category_id == cat_id:
                    return r
        # 最后匹配通用价
        for r in rows:
            if r.customer_id is None and r.category_id is None:
                return r
        return None

    async def save(self, s: AsyncSession, orm: SalCustomerPricingORM) -> SalCustomerPricingORM:
        s.add(orm); await s.flush(); return orm


# ────────────────────────────── 销售单据仓储 ──────────────────────────────


class SalesQuotationRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, qid: UUID) -> SalSalesQuotationORM | None:
        return (await s.execute(select(SalSalesQuotationORM).where(SalSalesQuotationORM.tenant_id == tid, SalSalesQuotationORM.quotation_id == qid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> SalSalesQuotationORM | None:
        return (await s.execute(select(SalSalesQuotationORM).where(SalSalesQuotationORM.tenant_id == tid, SalSalesQuotationORM.quotation_code == code))).scalar_one_or_none()

    async def list_by_customer(self, s: AsyncSession, tid: UUID, cid: UUID, offset: int = 0, limit: int = 50) -> list[SalSalesQuotationORM]:
        return list((await s.execute(select(SalSalesQuotationORM).where(SalSalesQuotationORM.tenant_id == tid, SalSalesQuotationORM.customer_id == cid).offset(offset).limit(limit))).scalars().all())

    async def list_by_status(self, s: AsyncSession, tid: UUID, status: str, offset: int = 0, limit: int = 50) -> list[SalSalesQuotationORM]:
        return list((await s.execute(select(SalSalesQuotationORM).where(SalSalesQuotationORM.tenant_id == tid, SalSalesQuotationORM.status == status).offset(offset).limit(limit))).scalars().all())

    async def list_expired(self, s: AsyncSession, tid: UUID, now: datetime) -> list[SalSalesQuotationORM]:
        """查过期报价（status=approved 且 valid_until < now）。"""
        return list((await s.execute(select(SalSalesQuotationORM).where(SalSalesQuotationORM.tenant_id == tid, SalSalesQuotationORM.status == "approved", SalSalesQuotationORM.valid_until < now))).scalars().all())

    async def list_effective(self, s: AsyncSession, tid: UUID, now: datetime, offset: int = 0, limit: int = 50) -> list[SalSalesQuotationORM]:
        return list((await s.execute(select(SalSalesQuotationORM).where(SalSalesQuotationORM.tenant_id == tid, SalSalesQuotationORM.status == "approved", SalSalesQuotationORM.valid_from <= now).offset(offset).limit(limit))).scalars().all())

    async def list_lines(self, s: AsyncSession, tid: UUID, qid: UUID) -> list[SalSalesQuotationLineORM]:
        return list((await s.execute(select(SalSalesQuotationLineORM).where(SalSalesQuotationLineORM.tenant_id == tid, SalSalesQuotationLineORM.quotation_id == qid))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalSalesQuotationORM) -> SalSalesQuotationORM:
        s.add(orm); await s.flush(); return orm

    async def save_line(self, s: AsyncSession, orm: SalSalesQuotationLineORM) -> SalSalesQuotationLineORM:
        s.add(orm); await s.flush(); return orm


class SalesOrderRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, oid: UUID) -> SalSalesOrderORM | None:
        return (await s.execute(select(SalSalesOrderORM).where(SalSalesOrderORM.tenant_id == tid, SalSalesOrderORM.order_id == oid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> SalSalesOrderORM | None:
        return (await s.execute(select(SalSalesOrderORM).where(SalSalesOrderORM.tenant_id == tid, SalSalesOrderORM.order_code == code))).scalar_one_or_none()

    async def get_by_idempotency_key(self, s: AsyncSession, tid: UUID, key: str) -> SalSalesOrderORM | None:
        return (await s.execute(select(SalSalesOrderORM).where(SalSalesOrderORM.tenant_id == tid, SalSalesOrderORM.idempotency_key == key))).scalar_one_or_none()

    async def list_by_customer(self, s: AsyncSession, tid: UUID, cid: UUID, offset: int = 0, limit: int = 50) -> list[SalSalesOrderORM]:
        return list((await s.execute(select(SalSalesOrderORM).where(SalSalesOrderORM.tenant_id == tid, SalSalesOrderORM.customer_id == cid).offset(offset).limit(limit))).scalars().all())

    async def list_by_status(self, s: AsyncSession, tid: UUID, status: str, offset: int = 0, limit: int = 50) -> list[SalSalesOrderORM]:
        return list((await s.execute(select(SalSalesOrderORM).where(SalSalesOrderORM.tenant_id == tid, SalSalesOrderORM.status == status).offset(offset).limit(limit))).scalars().all())

    async def list_by_tenant(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[SalSalesOrderORM]:
        return list((await s.execute(select(SalSalesOrderORM).where(SalSalesOrderORM.tenant_id == tid).offset(offset).limit(limit))).scalars().all())

    async def update_shipped_quantity(self, s: AsyncSession, tid: UUID, line_id: UUID, shipped_qty: float) -> None:
        await s.execute(update(SalSalesOrderLineORM).where(SalSalesOrderLineORM.tenant_id == tid, SalSalesOrderLineORM.line_id == line_id).values(shipped_quantity=shipped_qty))

    async def update_status(self, s: AsyncSession, tid: UUID, oid: UUID, status: str) -> None:
        await s.execute(update(SalSalesOrderORM).where(SalSalesOrderORM.tenant_id == tid, SalSalesOrderORM.order_id == oid).values(status=status))

    async def list_lines(self, s: AsyncSession, tid: UUID, oid: UUID) -> list[SalSalesOrderLineORM]:
        return list((await s.execute(select(SalSalesOrderLineORM).where(SalSalesOrderLineORM.tenant_id == tid, SalSalesOrderLineORM.order_id == oid))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalSalesOrderORM) -> SalSalesOrderORM:
        s.add(orm); await s.flush(); return orm

    async def save_line(self, s: AsyncSession, orm: SalSalesOrderLineORM) -> SalSalesOrderLineORM:
        s.add(orm); await s.flush(); return orm


class ShipmentOrderRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, sid: UUID) -> SalShipmentOrderORM | None:
        return (await s.execute(select(SalShipmentOrderORM).where(SalShipmentOrderORM.tenant_id == tid, SalShipmentOrderORM.shipment_id == sid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> SalShipmentOrderORM | None:
        return (await s.execute(select(SalShipmentOrderORM).where(SalShipmentOrderORM.tenant_id == tid, SalShipmentOrderORM.shipment_code == code))).scalar_one_or_none()

    async def get_by_idempotency_key(self, s: AsyncSession, tid: UUID, key: str) -> SalShipmentOrderORM | None:
        return (await s.execute(select(SalShipmentOrderORM).where(SalShipmentOrderORM.tenant_id == tid, SalShipmentOrderORM.idempotency_key == key))).scalar_one_or_none()

    async def list_by_order(self, s: AsyncSession, tid: UUID, oid: UUID, offset: int = 0, limit: int = 50) -> list[SalShipmentOrderORM]:
        """按关联订单查询（order_ids JSONB 数组包含 oid）。"""
        return list((await s.execute(select(SalShipmentOrderORM).where(SalShipmentOrderORM.tenant_id == tid, SalShipmentOrderORM.order_ids.contains([str(oid)])).offset(offset).limit(limit))).scalars().all())

    async def list_by_status(self, s: AsyncSession, tid: UUID, status: str, offset: int = 0, limit: int = 50) -> list[SalShipmentOrderORM]:
        return list((await s.execute(select(SalShipmentOrderORM).where(SalShipmentOrderORM.tenant_id == tid, SalShipmentOrderORM.status == status).offset(offset).limit(limit))).scalars().all())

    async def update_status(self, s: AsyncSession, tid: UUID, sid: UUID, status: str) -> None:
        await s.execute(update(SalShipmentOrderORM).where(SalShipmentOrderORM.tenant_id == tid, SalShipmentOrderORM.shipment_id == sid).values(status=status))

    async def list_lines(self, s: AsyncSession, tid: UUID, sid: UUID) -> list[SalShipmentLineORM]:
        return list((await s.execute(select(SalShipmentLineORM).where(SalShipmentLineORM.tenant_id == tid, SalShipmentLineORM.shipment_id == sid))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalShipmentOrderORM) -> SalShipmentOrderORM:
        s.add(orm); await s.flush(); return orm

    async def save_line(self, s: AsyncSession, orm: SalShipmentLineORM) -> SalShipmentLineORM:
        s.add(orm); await s.flush(); return orm


class PackingRecordRepository:
    async def get_by_shipment(self, s: AsyncSession, tid: UUID, sid: UUID) -> SalPackingRecordORM | None:
        return (await s.execute(select(SalPackingRecordORM).where(SalPackingRecordORM.tenant_id == tid, SalPackingRecordORM.shipment_id == sid))).scalar_one_or_none()

    async def get_by_id(self, s: AsyncSession, tid: UUID, pid: UUID) -> SalPackingRecordORM | None:
        return (await s.execute(select(SalPackingRecordORM).where(SalPackingRecordORM.tenant_id == tid, SalPackingRecordORM.packing_id == pid))).scalar_one_or_none()

    async def list_by_tenant(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[SalPackingRecordORM]:
        return list((await s.execute(select(SalPackingRecordORM).where(SalPackingRecordORM.tenant_id == tid).offset(offset).limit(limit))).scalars().all())

    async def list_lines(self, s: AsyncSession, tid: UUID, pid: UUID) -> list[SalPackingLineORM]:
        return list((await s.execute(select(SalPackingLineORM).where(SalPackingLineORM.tenant_id == tid, SalPackingLineORM.packing_id == pid))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalPackingRecordORM) -> SalPackingRecordORM:
        s.add(orm); await s.flush(); return orm

    async def save_line(self, s: AsyncSession, orm: SalPackingLineORM) -> SalPackingLineORM:
        s.add(orm); await s.flush(); return orm


class SalesReturnRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, rid: UUID) -> SalSalesReturnORM | None:
        return (await s.execute(select(SalSalesReturnORM).where(SalSalesReturnORM.tenant_id == tid, SalSalesReturnORM.return_id == rid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> SalSalesReturnORM | None:
        return (await s.execute(select(SalSalesReturnORM).where(SalSalesReturnORM.tenant_id == tid, SalSalesReturnORM.return_code == code))).scalar_one_or_none()

    async def get_by_idempotency_key(self, s: AsyncSession, tid: UUID, key: str) -> SalSalesReturnORM | None:
        return (await s.execute(select(SalSalesReturnORM).where(SalSalesReturnORM.tenant_id == tid, SalSalesReturnORM.idempotency_key == key))).scalar_one_or_none()

    async def list_by_order(self, s: AsyncSession, tid: UUID, oid: UUID, offset: int = 0, limit: int = 50) -> list[SalSalesReturnORM]:
        return list((await s.execute(select(SalSalesReturnORM).where(SalSalesReturnORM.tenant_id == tid, SalSalesReturnORM.order_id == oid).offset(offset).limit(limit))).scalars().all())

    async def list_by_status(self, s: AsyncSession, tid: UUID, status: str, offset: int = 0, limit: int = 50) -> list[SalSalesReturnORM]:
        return list((await s.execute(select(SalSalesReturnORM).where(SalSalesReturnORM.tenant_id == tid, SalSalesReturnORM.status == status).offset(offset).limit(limit))).scalars().all())

    async def list_lines(self, s: AsyncSession, tid: UUID, rid: UUID) -> list[SalReturnLineORM]:
        return list((await s.execute(select(SalReturnLineORM).where(SalReturnLineORM.tenant_id == tid, SalReturnLineORM.return_id == rid))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalSalesReturnORM) -> SalSalesReturnORM:
        s.add(orm); await s.flush(); return orm

    async def save_line(self, s: AsyncSession, orm: SalReturnLineORM) -> SalReturnLineORM:
        s.add(orm); await s.flush(); return orm


class SalesSettlementRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, sid: UUID) -> SalSalesSettlementORM | None:
        return (await s.execute(select(SalSalesSettlementORM).where(SalSalesSettlementORM.tenant_id == tid, SalSalesSettlementORM.settlement_id == sid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> SalSalesSettlementORM | None:
        return (await s.execute(select(SalSalesSettlementORM).where(SalSalesSettlementORM.tenant_id == tid, SalSalesSettlementORM.settlement_code == code))).scalar_one_or_none()

    async def get_by_order(self, s: AsyncSession, tid: UUID, oid: UUID) -> SalSalesSettlementORM | None:
        return (await s.execute(select(SalSalesSettlementORM).where(SalSalesSettlementORM.tenant_id == tid, SalSalesSettlementORM.order_id == oid))).scalar_one_or_none()

    async def list_by_status(self, s: AsyncSession, tid: UUID, status: str, offset: int = 0, limit: int = 50) -> list[SalSalesSettlementORM]:
        return list((await s.execute(select(SalSalesSettlementORM).where(SalSalesSettlementORM.tenant_id == tid, SalSalesSettlementORM.status == status).offset(offset).limit(limit))).scalars().all())

    async def update_status(self, s: AsyncSession, tid: UUID, sid: UUID, status: str) -> None:
        await s.execute(update(SalSalesSettlementORM).where(SalSalesSettlementORM.tenant_id == tid, SalSalesSettlementORM.settlement_id == sid).values(status=status))

    async def list_reconcile_lines(self, s: AsyncSession, tid: UUID, sid: UUID) -> list[SalSettlementReconcileLineORM]:
        return list((await s.execute(select(SalSettlementReconcileLineORM).where(SalSettlementReconcileLineORM.tenant_id == tid, SalSettlementReconcileLineORM.settlement_id == sid))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalSalesSettlementORM) -> SalSalesSettlementORM:
        s.add(orm); await s.flush(); return orm

    async def save_reconcile_line(self, s: AsyncSession, orm: SalSettlementReconcileLineORM) -> SalSettlementReconcileLineORM:
        s.add(orm); await s.flush(); return orm


class SalesInvoiceRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, iid: UUID) -> SalSalesInvoiceORM | None:
        return (await s.execute(select(SalSalesInvoiceORM).where(SalSalesInvoiceORM.tenant_id == tid, SalSalesInvoiceORM.invoice_id == iid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> SalSalesInvoiceORM | None:
        return (await s.execute(select(SalSalesInvoiceORM).where(SalSalesInvoiceORM.tenant_id == tid, SalSalesInvoiceORM.invoice_code == code))).scalar_one_or_none()

    async def list_by_customer(self, s: AsyncSession, tid: UUID, cid: UUID, offset: int = 0, limit: int = 50) -> list[SalSalesInvoiceORM]:
        return list((await s.execute(select(SalSalesInvoiceORM).where(SalSalesInvoiceORM.tenant_id == tid, SalSalesInvoiceORM.customer_id == cid).offset(offset).limit(limit))).scalars().all())

    async def list_by_status(self, s: AsyncSession, tid: UUID, status: str, offset: int = 0, limit: int = 50) -> list[SalSalesInvoiceORM]:
        return list((await s.execute(select(SalSalesInvoiceORM).where(SalSalesInvoiceORM.tenant_id == tid, SalSalesInvoiceORM.status == status).offset(offset).limit(limit))).scalars().all())

    async def list_lines(self, s: AsyncSession, tid: UUID, iid: UUID) -> list[SalInvoiceLineORM]:
        return list((await s.execute(select(SalInvoiceLineORM).where(SalInvoiceLineORM.tenant_id == tid, SalInvoiceLineORM.invoice_id == iid))).scalars().all())

    async def save(self, s: AsyncSession, orm: SalSalesInvoiceORM) -> SalSalesInvoiceORM:
        s.add(orm); await s.flush(); return orm

    async def save_line(self, s: AsyncSession, orm: SalInvoiceLineORM) -> SalInvoiceLineORM:
        s.add(orm); await s.flush(); return orm


class PaymentReceiptRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, pid: UUID) -> SalPaymentReceiptORM | None:
        return (await s.execute(select(SalPaymentReceiptORM).where(SalPaymentReceiptORM.tenant_id == tid, SalPaymentReceiptORM.payment_receipt_id == pid))).scalar_one_or_none()

    async def get_by_settlement(self, s: AsyncSession, tid: UUID, sid: UUID) -> SalPaymentReceiptORM | None:
        return (await s.execute(select(SalPaymentReceiptORM).where(SalPaymentReceiptORM.tenant_id == tid, SalPaymentReceiptORM.settlement_id == sid))).scalar_one_or_none()

    async def list_by_status(self, s: AsyncSession, tid: UUID, status: str, offset: int = 0, limit: int = 50) -> list[SalPaymentReceiptORM]:
        return list((await s.execute(select(SalPaymentReceiptORM).where(SalPaymentReceiptORM.tenant_id == tid, SalPaymentReceiptORM.status == status).offset(offset).limit(limit))).scalars().all())

    async def update_status(self, s: AsyncSession, tid: UUID, pid: UUID, status: str) -> None:
        await s.execute(update(SalPaymentReceiptORM).where(SalPaymentReceiptORM.tenant_id == tid, SalPaymentReceiptORM.payment_receipt_id == pid).values(status=status))

    async def save(self, s: AsyncSession, orm: SalPaymentReceiptORM) -> SalPaymentReceiptORM:
        s.add(orm); await s.flush(); return orm


# ────────────────────────────── 审计仓储 ──────────────────────────────


class SalesAuditRepository:
    """append-only 审计仓储 - 仅 INSERT/SELECT，通过 REVOKE UPDATE/DELETE + Trigger 双保险确保不可变。"""

    async def append(self, s: AsyncSession, orm: SalSalesAuditORM) -> SalSalesAuditORM:
        s.add(orm); await s.flush(); return orm

    async def query_by_order(self, s: AsyncSession, tid: UUID, oid: UUID, offset: int = 0, limit: int = 100) -> list[SalSalesAuditORM]:
        return list((await s.execute(select(SalSalesAuditORM).where(SalSalesAuditORM.tenant_id == tid, SalSalesAuditORM.order_id == oid).offset(offset).limit(limit))).scalars().all())

    async def query_by_customer(self, s: AsyncSession, tid: UUID, cid: UUID, offset: int = 0, limit: int = 100) -> list[SalSalesAuditORM]:
        return list((await s.execute(select(SalSalesAuditORM).where(SalSalesAuditORM.tenant_id == tid, SalSalesAuditORM.customer_id == cid).offset(offset).limit(limit))).scalars().all())

    async def query_by_time_range(self, s: AsyncSession, tid: UUID, start: datetime, end: datetime, offset: int = 0, limit: int = 100) -> list[SalSalesAuditORM]:
        return list((await s.execute(select(SalSalesAuditORM).where(SalSalesAuditORM.tenant_id == tid, SalSalesAuditORM.operated_at >= start, SalSalesAuditORM.operated_at <= end).offset(offset).limit(limit))).scalars().all())