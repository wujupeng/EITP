"""PUR 仓储实现 - 供应商/报价/评估/申请/订单/到货/退货/结算/发票/付款。

企业级表含 tenant_id，查询自动过滤租户。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.purchasing.models import (
    PurAsnORM, PurInvoiceORM, PurPaymentRequestORM, PurPurchaseAuditORM,
    PurPurchaseOrderORM, PurPurchaseOrderLineORM, PurPurchaseReceiptORM,
    PurPurchaseReceiptLineORM, PurPurchaseRequestORM, PurPurchaseRequestLineORM,
    PurPurchaseReturnORM, PurPurchaseReturnLineORM, PurPurchaseSettlementORM,
    PurQuotationORM, PurQuotationLineORM, PurReconcileDiffORM,
    PurSupplierEvaluationORM, PurSupplierORM, PurSupplierScopeORM,
)


class SupplierRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, sid: UUID) -> PurSupplierORM | None:
        return (await s.execute(select(PurSupplierORM).where(PurSupplierORM.tenant_id == tid, PurSupplierORM.supplier_id == sid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> PurSupplierORM | None:
        return (await s.execute(select(PurSupplierORM).where(PurSupplierORM.tenant_id == tid, PurSupplierORM.supplier_code == code))).scalar_one_or_none()

    async def list_by_tenant(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[PurSupplierORM]:
        return list((await s.execute(select(PurSupplierORM).where(PurSupplierORM.tenant_id == tid).offset(offset).limit(limit))).scalars().all())

    async def save(self, s: AsyncSession, orm: PurSupplierORM) -> PurSupplierORM:
        s.add(orm); await s.flush(); return orm


class SupplierScopeRepository:
    async def list_by_supplier(self, s: AsyncSession, tid: UUID, sid: UUID) -> list[PurSupplierScopeORM]:
        return list((await s.execute(select(PurSupplierScopeORM).where(PurSupplierScopeORM.tenant_id == tid, PurSupplierScopeORM.supplier_id == sid))).scalars().all())

    async def save(self, s: AsyncSession, orm: PurSupplierScopeORM) -> PurSupplierScopeORM:
        s.add(orm); await s.flush(); return orm


class QuotationRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, qid: UUID) -> PurQuotationORM | None:
        return (await s.execute(select(PurQuotationORM).where(PurQuotationORM.tenant_id == tid, PurQuotationORM.quotation_id == qid))).scalar_one_or_none()

    async def save(self, s: AsyncSession, orm: PurQuotationORM) -> PurQuotationORM:
        s.add(orm); await s.flush(); return orm


class SupplierEvaluationRepository:
    async def save(self, s: AsyncSession, orm: PurSupplierEvaluationORM) -> PurSupplierEvaluationORM:
        s.add(orm); await s.flush(); return orm


class PurchaseRequestRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, rid: UUID) -> PurPurchaseRequestORM | None:
        return (await s.execute(select(PurPurchaseRequestORM).where(PurPurchaseRequestORM.tenant_id == tid, PurPurchaseRequestORM.request_id == rid))).scalar_one_or_none()

    async def list_by_tenant(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[PurPurchaseRequestORM]:
        return list((await s.execute(select(PurPurchaseRequestORM).where(PurPurchaseRequestORM.tenant_id == tid).offset(offset).limit(limit))).scalars().all())

    async def save(self, s: AsyncSession, orm: PurPurchaseRequestORM) -> PurPurchaseRequestORM:
        s.add(orm); await s.flush(); return orm

    async def list_lines(self, s: AsyncSession, tid: UUID, rid: UUID) -> list[PurPurchaseRequestLineORM]:
        return list((await s.execute(select(PurPurchaseRequestLineORM).where(PurPurchaseRequestLineORM.tenant_id == tid, PurPurchaseRequestLineORM.request_id == rid))).scalars().all())


class PurchaseOrderRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, oid: UUID) -> PurPurchaseOrderORM | None:
        return (await s.execute(select(PurPurchaseOrderORM).where(PurPurchaseOrderORM.tenant_id == tid, PurPurchaseOrderORM.order_id == oid))).scalar_one_or_none()

    async def get_by_code(self, s: AsyncSession, tid: UUID, code: str) -> PurPurchaseOrderORM | None:
        return (await s.execute(select(PurPurchaseOrderORM).where(PurPurchaseOrderORM.tenant_id == tid, PurPurchaseOrderORM.order_code == code))).scalar_one_or_none()

    async def list_by_tenant(self, s: AsyncSession, tid: UUID, offset: int = 0, limit: int = 50) -> list[PurPurchaseOrderORM]:
        return list((await s.execute(select(PurPurchaseOrderORM).where(PurPurchaseOrderORM.tenant_id == tid).offset(offset).limit(limit))).scalars().all())

    async def save(self, s: AsyncSession, orm: PurPurchaseOrderORM) -> PurPurchaseOrderORM:
        s.add(orm); await s.flush(); return orm

    async def list_lines(self, s: AsyncSession, tid: UUID, oid: UUID) -> list[PurPurchaseOrderLineORM]:
        return list((await s.execute(select(PurPurchaseOrderLineORM).where(PurPurchaseOrderLineORM.tenant_id == tid, PurPurchaseOrderLineORM.order_id == oid))).scalars().all())

    async def save_line(self, s: AsyncSession, orm: PurPurchaseOrderLineORM) -> PurPurchaseOrderLineORM:
        s.add(orm); await s.flush(); return orm


class AsnRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, aid: UUID) -> PurAsnORM | None:
        return (await s.execute(select(PurAsnORM).where(PurAsnORM.tenant_id == tid, PurAsnORM.asn_id == aid))).scalar_one_or_none()

    async def save(self, s: AsyncSession, orm: PurAsnORM) -> PurAsnORM:
        s.add(orm); await s.flush(); return orm


class PurchaseReceiptRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, rid: UUID) -> PurPurchaseReceiptORM | None:
        return (await s.execute(select(PurPurchaseReceiptORM).where(PurPurchaseReceiptORM.tenant_id == tid, PurPurchaseReceiptORM.receipt_id == rid))).scalar_one_or_none()

    async def save(self, s: AsyncSession, orm: PurPurchaseReceiptORM) -> PurPurchaseReceiptORM:
        s.add(orm); await s.flush(); return orm

    async def list_lines(self, s: AsyncSession, tid: UUID, rid: UUID) -> list[PurPurchaseReceiptLineORM]:
        return list((await s.execute(select(PurPurchaseReceiptLineORM).where(PurPurchaseReceiptLineORM.tenant_id == tid, PurPurchaseReceiptLineORM.receipt_id == rid))).scalars().all())


class PurchaseReturnRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, rid: UUID) -> PurPurchaseReturnORM | None:
        return (await s.execute(select(PurPurchaseReturnORM).where(PurPurchaseReturnORM.tenant_id == tid, PurPurchaseReturnORM.return_id == rid))).scalar_one_or_none()

    async def save(self, s: AsyncSession, orm: PurPurchaseReturnORM) -> PurPurchaseReturnORM:
        s.add(orm); await s.flush(); return orm

    async def list_lines(self, s: AsyncSession, tid: UUID, rid: UUID) -> list[PurPurchaseReturnLineORM]:
        return list((await s.execute(select(PurPurchaseReturnLineORM).where(PurPurchaseReturnLineORM.tenant_id == tid, PurPurchaseReturnLineORM.return_id == rid))).scalars().all())


class PurchaseSettlementRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, sid: UUID) -> PurPurchaseSettlementORM | None:
        return (await s.execute(select(PurPurchaseSettlementORM).where(PurPurchaseSettlementORM.tenant_id == tid, PurPurchaseSettlementORM.settlement_id == sid))).scalar_one_or_none()

    async def save(self, s: AsyncSession, orm: PurPurchaseSettlementORM) -> PurPurchaseSettlementORM:
        s.add(orm); await s.flush(); return orm


class InvoiceRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, iid: UUID) -> PurInvoiceORM | None:
        return (await s.execute(select(PurInvoiceORM).where(PurInvoiceORM.tenant_id == tid, PurInvoiceORM.invoice_id == iid))).scalar_one_or_none()

    async def save(self, s: AsyncSession, orm: PurInvoiceORM) -> PurInvoiceORM:
        s.add(orm); await s.flush(); return orm


class PaymentRequestRepository:
    async def get_by_id(self, s: AsyncSession, tid: UUID, pid: UUID) -> PurPaymentRequestORM | None:
        return (await s.execute(select(PurPaymentRequestORM).where(PurPaymentRequestORM.tenant_id == tid, PurPaymentRequestORM.payment_id == pid))).scalar_one_or_none()

    async def save(self, s: AsyncSession, orm: PurPaymentRequestORM) -> PurPaymentRequestORM:
        s.add(orm); await s.flush(); return orm


class PurchaseAuditRepository:
    async def save(self, s: AsyncSession, orm: PurPurchaseAuditORM) -> PurPurchaseAuditORM:
        s.add(orm); await s.flush(); return orm


class PurReconcileDiffRepository:
    async def list_open(self, s: AsyncSession, tid: UUID) -> list[PurReconcileDiffORM]:
        return list((await s.execute(select(PurReconcileDiffORM).where(PurReconcileDiffORM.tenant_id == tid, PurReconcileDiffORM.status == "open"))).scalars().all())

    async def save(self, s: AsyncSession, orm: PurReconcileDiffORM) -> PurReconcileDiffORM:
        s.add(orm); await s.flush(); return orm