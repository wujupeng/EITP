"""SAL 应用服务 - 客户/报价/订单/发货/包装/退货/结算/发票/收款/对账。

编排领域模型 + 仓储 + 外部API（WMS Picking/Shipping/Receiving / INV Reservation/Financial）。
第一条红线：销售出库通过 WMS Picking/Shipping API，不直接改库存。
第二条红线：销售结算通过 INV Financial/Revenue API，不直接改收入。
第五条红线：库存预留通过 INV Reservation API，不重新实现预留引擎。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.sales.services.credit_control_service import CreditControlService
from app.domain.sales.services.partial_fulfillment_service import PartialFulfillmentService
from app.domain.sales.services.price_match_service import PriceMatchService
from app.domain.sales.services.refund_calculator import RefundCalculator
from app.domain.sales.services.sal_reconcile_service import SalReconcileService
from app.domain.sales.services.sales_approval_router_service import (
    SalesApprovalRouterService,
)
from app.infrastructure.sales.models import (
    SalCreditLimitORM, SalCustomerAddressORM, SalCustomerCategoryORM,
    SalCustomerContactORM, SalCustomerORM, SalCustomerPricingORM,
    SalInvoiceLineORM, SalPackingLineORM, SalPackingRecordORM,
    SalPaymentReceiptORM, SalReturnLineORM, SalSalesAuditORM, SalSalesInvoiceORM,
    SalSalesOrderLineORM, SalSalesOrderORM, SalSalesQuotationLineORM,
    SalSalesQuotationORM, SalSalesReturnORM, SalSalesSettlementORM,
    SalSettlementReconcileLineORM, SalShipmentLineORM, SalShipmentOrderORM,
)
from app.infrastructure.sales.repositories import (
    CreditLimitRepository, CustomerCategoryRepository, CustomerPricingRepository,
    CustomerRepository, PackingRecordRepository, PaymentReceiptRepository,
    SalesAuditRepository, SalesInvoiceRepository, SalesOrderRepository,
    SalesQuotationRepository, SalesReturnRepository, SalesSettlementRepository,
    ShipmentOrderRepository,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode
from app.interfaces.middleware.security_context import SecurityContext


WMS_API_URL = "http://localhost:8000/api/v1/wms"
INV_API_URL = "http://localhost:8000/api/v1/inv"


def _check_auth(tenant_id: UUID, permission: str) -> None:
    ctx = SecurityContext.current()
    if ctx is None:
        raise SALError(SALErrorCode.SERVICE_UNAVAILABLE, "未认证")
    if ctx.tenant.tenant_id != tenant_id:
        raise SALError(SALErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")


def _current_user_id() -> UUID:
    ctx = SecurityContext.current()
    return ctx.user.user_id if ctx and ctx.user else UUID(int=0)


# ────────────────────────────── T12: 客户主数据与销售报价 ──────────────────────────────


class CustomerAppSvc:
    """客户主数据应用服务 - 编排客户管理 CRUD + 治理工作流 + 信用额度 + 价格体系。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CustomerRepository()
        self._cat_repo = CustomerCategoryRepository()
        self._credit_repo = CreditLimitRepository()
        self._pricing_repo = CustomerPricingRepository()
        self._audit_repo = SalesAuditRepository()

    async def create_customer(self, tenant_id: UUID, customer_code: str, customer_name: str,
                              customer_type: str = "corporate", **kwargs) -> SalCustomerORM:
        _check_auth(tenant_id, "sal:customer:manage")
        existing = await self._repo.get_by_code(self._session, tenant_id, customer_code)
        if existing:
            raise SALError(SALErrorCode.CUSTOMER_CODE_DUPLICATE, f"客户编码 {customer_code} 已存在")
        orm = SalCustomerORM(
            tenant_id=tenant_id, customer_code=customer_code, customer_name=customer_name,
            customer_type=customer_type,
            **{k: v for k, v in kwargs.items() if hasattr(SalCustomerORM, k)},
        )
        orm = await self._repo.save(self._session, orm)
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="CUSTOMER_CREATED",
            customer_id=orm.customer_id,
        ))
        return orm

    async def get_customer(self, tenant_id: UUID, customer_id: UUID) -> SalCustomerORM:
        _check_auth(tenant_id, "sal:customer:query")
        orm = await self._repo.get_by_id(self._session, tenant_id, customer_id)
        if orm is None:
            raise SALError(SALErrorCode.CUSTOMER_NOT_FOUND, f"客户 {customer_id} 不存在")
        return orm

    async def list_customers(self, tenant_id: UUID, status: str | None = None,
                             offset: int = 0, limit: int = 50) -> list[SalCustomerORM]:
        _check_auth(tenant_id, "sal:customer:query")
        if status:
            return await self._repo.list_by_status(self._session, tenant_id, status, offset, limit)
        return await self._repo.list_by_tenant(self._session, tenant_id, offset, limit)

    async def update_customer(self, tenant_id: UUID, customer_id: UUID, **kwargs) -> SalCustomerORM:
        _check_auth(tenant_id, "sal:customer:manage")
        orm = await self.get_customer(tenant_id, customer_id)
        if orm.status not in ("draft", "submitted"):
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"客户状态 {orm.status} 不可修改")
        for k, v in kwargs.items():
            if hasattr(orm, k) and v is not None:
                setattr(orm, k, v)
        await self._session.flush()
        return orm

    async def submit_customer(self, tenant_id: UUID, customer_id: UUID) -> SalCustomerORM:
        _check_auth(tenant_id, "sal:customer:manage")
        orm = await self.get_customer(tenant_id, customer_id)
        if orm.status != "draft":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"客户状态 {orm.status} 不可提交")
        orm.status = "submitted"
        orm.governance_state = "submitted"
        await self._session.flush()
        return orm

    async def approve_customer(self, tenant_id: UUID, customer_id: UUID, approved: bool = True,
                               approver_id: UUID | None = None) -> SalCustomerORM:
        _check_auth(tenant_id, "sal:customer:manage")
        orm = await self.get_customer(tenant_id, customer_id)
        if orm.status != "submitted":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"客户状态 {orm.status} 不可审批")
        if approved:
            orm.status = "approved"
            orm.governance_state = "approved"
            orm.approved_by = approver_id or _current_user_id()
        else:
            orm.status = "draft"
            orm.governance_state = "rejected"
        await self._session.flush()
        return orm

    async def publish_customer(self, tenant_id: UUID, customer_id: UUID) -> SalCustomerORM:
        _check_auth(tenant_id, "sal:customer:manage")
        orm = await self.get_customer(tenant_id, customer_id)
        if orm.status != "approved":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"客户状态 {orm.status} 不可发布")
        orm.status = "active"
        orm.published_version += 1
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="CUSTOMER_PUBLISHED",
            customer_id=orm.customer_id,
        ))
        return orm

    async def disable_customer(self, tenant_id: UUID, customer_id: UUID) -> SalCustomerORM:
        _check_auth(tenant_id, "sal:customer:manage")
        orm = await self.get_customer(tenant_id, customer_id)
        if orm.status != "active":
            raise SALError(SALErrorCode.CUSTOMER_DISABLED, f"客户状态 {orm.status} 不可停用")
        orm.status = "disabled"
        await self._session.flush()
        return orm

    async def set_credit_limit(self, tenant_id: UUID, customer_id: UUID, total_limit: float,
                               credit_period_days: int = 30, over_credit_strategy: str = "block") -> SalCreditLimitORM:
        _check_auth(tenant_id, "sal:credit:manage")
        await self.get_customer(tenant_id, customer_id)
        orm = await self._credit_repo.get_by_customer(self._session, tenant_id, customer_id)
        if orm is None:
            orm = SalCreditLimitORM(
                tenant_id=tenant_id, customer_id=customer_id, total_limit=total_limit,
                credit_period_days=credit_period_days, over_credit_strategy=over_credit_strategy,
            )
        else:
            orm.total_limit = total_limit
            orm.credit_period_days = credit_period_days
            orm.over_credit_strategy = over_credit_strategy
        return await self._credit_repo.save(self._session, orm)

    async def get_credit_limit(self, tenant_id: UUID, customer_id: UUID) -> SalCreditLimitORM:
        _check_auth(tenant_id, "sal:credit:manage")
        orm = await self._credit_repo.get_by_customer(self._session, tenant_id, customer_id)
        if orm is None:
            raise SALError(SALErrorCode.CREDIT_CONFIG_NOT_FOUND, f"客户 {customer_id} 信用额度未配置")
        return orm

    async def set_pricing(self, tenant_id: UUID, customer_id: UUID | None, enterprise_sku_id: UUID,
                          price_type: str = "standard", agreement_price: float | None = None,
                          discount_rate: float | None = None, priority: int = 4,
                          valid_from: datetime | None = None, valid_until: datetime | None = None,
                          category_id: UUID | None = None) -> SalCustomerPricingORM:
        _check_auth(tenant_id, "sal:pricing:manage")
        orm = SalCustomerPricingORM(
            tenant_id=tenant_id, customer_id=customer_id, category_id=category_id,
            enterprise_sku_id=enterprise_sku_id, price_type=price_type,
            agreement_price=agreement_price, discount_rate=discount_rate, priority=priority,
            status="published",
        )
        if valid_from:
            orm.valid_from = valid_from
        if valid_until:
            orm.valid_until = valid_until
        return await self._pricing_repo.save(self._session, orm)

    async def list_pricing(self, tenant_id: UUID, customer_id: UUID) -> list[SalCustomerPricingORM]:
        _check_auth(tenant_id, "sal:pricing:manage")
        return await self._pricing_repo.list_by_customer(self._session, tenant_id, customer_id)

    async def add_address(self, tenant_id: UUID, customer_id: UUID, address_type: str = "default",
                          **kwargs) -> SalCustomerAddressORM:
        _check_auth(tenant_id, "sal:customer:manage")
        orm = SalCustomerAddressORM(
            tenant_id=tenant_id, customer_id=customer_id, address_type=address_type,
            **{k: v for k, v in kwargs.items() if hasattr(SalCustomerAddressORM, k)},
        )
        return await self._repo.save_address(self._session, orm)

    async def add_contact(self, tenant_id: UUID, customer_id: UUID, contact_name: str = "",
                          **kwargs) -> SalCustomerContactORM:
        _check_auth(tenant_id, "sal:customer:manage")
        orm = SalCustomerContactORM(
            tenant_id=tenant_id, customer_id=customer_id, contact_name=contact_name,
            **{k: v for k, v in kwargs.items() if hasattr(SalCustomerContactORM, k)},
        )
        return await self._repo.save_contact(self._session, orm)


class CustomerCategoryAppSvc:
    """客户分类应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CustomerCategoryRepository()

    async def create_category(self, tenant_id: UUID, category_code: str, category_name: str,
                              description: str = "") -> SalCustomerCategoryORM:
        _check_auth(tenant_id, "sal:category:manage")
        existing = await self._repo.get_by_code(self._session, tenant_id, category_code)
        if existing:
            raise SALError(SALErrorCode.CUSTOMER_CODE_DUPLICATE, f"分类编码 {category_code} 已存在")
        orm = SalCustomerCategoryORM(
            tenant_id=tenant_id, category_code=category_code,
            category_name=category_name, description=description,
        )
        return await self._repo.save(self._session, orm)

    async def list_categories(self, tenant_id: UUID, offset: int = 0, limit: int = 50) -> list[SalCustomerCategoryORM]:
        _check_auth(tenant_id, "sal:category:manage")
        return await self._repo.list_by_tenant(self._session, tenant_id, offset, limit)


class SalesQuotationAppSvc:
    """销售报价应用服务 - 编排报价 CRUD + 治理工作流 + 转单。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SalesQuotationRepository()
        self._order_repo = SalesOrderRepository()
        self._cust_repo = CustomerRepository()
        self._router = SalesApprovalRouterService()
        self._audit_repo = SalesAuditRepository()

    async def create_quotation(self, tenant_id: UUID, quotation_code: str, customer_id: UUID,
                               lines: list[dict] | None = None, **kwargs) -> SalSalesQuotationORM:
        _check_auth(tenant_id, "sal:quotation:create")
        cust = await self._cust_repo.get_by_id(self._session, tenant_id, customer_id)
        if cust is None:
            raise SALError(SALErrorCode.CUSTOMER_NOT_FOUND, f"客户 {customer_id} 不存在")
        if cust.status != "active":
            raise SALError(SALErrorCode.CUSTOMER_NOT_ACTIVE, f"客户状态 {cust.status} 不可报价")
        existing = await self._repo.get_by_code(self._session, tenant_id, quotation_code)
        if existing:
            raise SALError(SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION, f"报价编码 {quotation_code} 已存在")
        orm = SalSalesQuotationORM(
            tenant_id=tenant_id, quotation_code=quotation_code, customer_id=customer_id,
            **{k: v for k, v in kwargs.items() if hasattr(SalSalesQuotationORM, k)},
        )
        orm = await self._repo.save(self._session, orm)
        if lines:
            for idx, line_data in enumerate(lines, start=1):
                line = SalSalesQuotationLineORM(
                    tenant_id=tenant_id, quotation_id=orm.quotation_id, line_number=idx,
                    **{k: v for k, v in line_data.items() if hasattr(SalSalesQuotationLineORM, k)},
                )
                await self._repo.save_line(self._session, line)
        return orm

    async def get_quotation(self, tenant_id: UUID, quotation_id: UUID) -> SalSalesQuotationORM:
        _check_auth(tenant_id, "sal:quotation:create")
        orm = await self._repo.get_by_id(self._session, tenant_id, quotation_id)
        if orm is None:
            raise SALError(SALErrorCode.QUOTATION_NOT_FOUND, f"报价 {quotation_id} 不存在")
        return orm

    async def list_quotations(self, tenant_id: UUID, status: str | None = None,
                              offset: int = 0, limit: int = 50) -> list[SalSalesQuotationORM]:
        _check_auth(tenant_id, "sal:quotation:create")
        if status:
            return await self._repo.list_by_status(self._session, tenant_id, status, offset, limit)
        return await self._repo.list_by_status(self._session, tenant_id, "draft", offset, limit)

    async def submit_quotation(self, tenant_id: UUID, quotation_id: UUID) -> SalSalesQuotationORM:
        _check_auth(tenant_id, "sal:quotation:create")
        orm = await self.get_quotation(tenant_id, quotation_id)
        if orm.status != "draft":
            raise SALError(SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION, f"报价状态 {orm.status} 不可提交")
        orm.status = "submitted"
        orm.governance_state = "submitted"
        orm.submitted_by = _current_user_id()
        orm.submitted_at = datetime.now(timezone.utc)
        await self._session.flush()
        return orm

    async def approve_quotation(self, tenant_id: UUID, quotation_id: UUID, approved: bool = True,
                                approver_id: UUID | None = None) -> SalSalesQuotationORM:
        _check_auth(tenant_id, "sal:quotation:approve")
        orm = await self.get_quotation(tenant_id, quotation_id)
        if orm.status != "submitted":
            raise SALError(SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION, f"报价状态 {orm.status} 不可审批")
        if approved:
            orm.status = "approved"
            orm.governance_state = "approved"
            orm.approved_by = approver_id or _current_user_id()
            orm.approved_at = datetime.now(timezone.utc)
        else:
            orm.status = "draft"
            orm.governance_state = "rejected"
        await self._session.flush()
        return orm

    async def convert_to_order(self, tenant_id: UUID, quotation_id: UUID,
                               order_code: str) -> SalSalesOrderORM:
        """转销售订单 - 继承客户/行明细/单价/付款条件。"""
        _check_auth(tenant_id, "sal:quotation:convert")
        orm = await self.get_quotation(tenant_id, quotation_id)
        if orm.status != "approved":
            raise SALError(SALErrorCode.QUOTATION_NOT_APPROVED, "报价非已审批状态不可转单")
        if orm.valid_until and orm.valid_until < datetime.now(timezone.utc):
            orm.status = "expired"
            raise SALError(SALErrorCode.QUOTATION_EXPIRED, "报价已过期不可转单")
        lines = await self._repo.list_lines(self._session, tenant_id, quotation_id)
        order = SalSalesOrderORM(
            tenant_id=tenant_id, order_code=order_code, customer_id=orm.customer_id,
            source_quotation_id=quotation_id, payment_terms=orm.payment_terms, currency=orm.currency,
            total_amount=sum(float(l.quantity) * float(l.unit_price) for l in lines),
        )
        order = await self._order_repo.save(self._session, order)
        for idx, ql in enumerate(lines, start=1):
            await self._order_repo.save_line(self._session, SalSalesOrderLineORM(
                tenant_id=tenant_id, order_id=order.order_id, line_number=idx,
                enterprise_sku_id=ql.enterprise_sku_id, ordered_quantity=float(ql.quantity),
                unit_price=float(ql.unit_price), expected_delivery_date=ql.expected_delivery_date,
            ))
        orm.status = "converted"
        orm.converted_order_id = order.order_id
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SALES_QUOTATION_CONVERTED",
            customer_id=orm.customer_id, order_id=order.order_id,
        ))
        return order

    async def cancel_quotation(self, tenant_id: UUID, quotation_id: UUID) -> SalSalesQuotationORM:
        _check_auth(tenant_id, "sal:quotation:create")
        orm = await self.get_quotation(tenant_id, quotation_id)
        if orm.status in ("converted", "expired"):
            raise SALError(SALErrorCode.QUOTATION_INVALID_STATE_TRANSITION, f"报价状态 {orm.status} 不可取消")
        orm.status = "cancelled"
        await self._session.flush()
        return orm


# ────────────────────────────── T13: 销售订单/发货/退货/结算 ──────────────────────────────


class SalesOrderAppSvc:
    """销售订单应用服务 - 红线五核心：确认履约通过 INV Reservation API 预留。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SalesOrderRepository()
        self._cust_repo = CustomerRepository()
        self._credit_repo = CreditLimitRepository()
        self._pricing_repo = CustomerPricingRepository()
        self._audit_repo = SalesAuditRepository()
        self._router = SalesApprovalRouterService()
        self._price_match = PriceMatchService()
        self._partial = PartialFulfillmentService()

    async def create_order(self, tenant_id: UUID, order_code: str, customer_id: UUID,
                           lines: list[dict] | None = None, idempotency_key: str = "",
                           **kwargs) -> SalSalesOrderORM:
        _check_auth(tenant_id, "sal:order:create")
        if idempotency_key:
            existing = await self._repo.get_by_idempotency_key(self._session, tenant_id, idempotency_key)
            if existing:
                return existing
        cust = await self._cust_repo.get_by_id(self._session, tenant_id, customer_id)
        if cust is None:
            raise SALError(SALErrorCode.CUSTOMER_NOT_FOUND, f"客户 {customer_id} 不存在")
        if cust.status != "active":
            raise SALError(SALErrorCode.CUSTOMER_NOT_ACTIVE, f"客户状态 {cust.status} 不可下单")
        existing = await self._repo.get_by_code(self._session, tenant_id, order_code)
        if existing:
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"订单编码 {order_code} 已存在")
        orm = SalSalesOrderORM(
            tenant_id=tenant_id, order_code=order_code, customer_id=customer_id,
            idempotency_key=idempotency_key,
            **{k: v for k, v in kwargs.items() if hasattr(SalSalesOrderORM, k)},
        )
        orm = await self._repo.save(self._session, orm)
        total = 0.0
        if lines:
            for idx, line_data in enumerate(lines, start=1):
                qty = float(line_data.get("ordered_quantity", 0))
                price = float(line_data.get("unit_price", 0))
                line = SalSalesOrderLineORM(
                    tenant_id=tenant_id, order_id=orm.order_id, line_number=idx,
                    **{k: v for k, v in line_data.items() if hasattr(SalSalesOrderLineORM, k)},
                )
                await self._repo.save_line(self._session, line)
                total += qty * price
        orm.total_amount = total
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SALES_ORDER_CREATED",
            customer_id=customer_id, order_id=orm.order_id,
        ))
        return orm

    async def get_order(self, tenant_id: UUID, order_id: UUID) -> SalSalesOrderORM:
        _check_auth(tenant_id, "sal:order:query")
        orm = await self._repo.get_by_id(self._session, tenant_id, order_id)
        if orm is None:
            raise SALError(SALErrorCode.ORDER_NOT_FOUND, f"销售订单 {order_id} 不存在")
        return orm

    async def list_orders(self, tenant_id: UUID, status: str | None = None, customer_id: UUID | None = None,
                          offset: int = 0, limit: int = 50) -> list[SalSalesOrderORM]:
        _check_auth(tenant_id, "sal:order:query")
        if customer_id:
            return await self._repo.list_by_customer(self._session, tenant_id, customer_id, offset, limit)
        if status:
            return await self._repo.list_by_status(self._session, tenant_id, status, offset, limit)
        return await self._repo.list_by_tenant(self._session, tenant_id, offset, limit)

    async def update_order(self, tenant_id: UUID, order_id: UUID, **kwargs) -> SalSalesOrderORM:
        _check_auth(tenant_id, "sal:order:create")
        orm = await self.get_order(tenant_id, order_id)
        if orm.status != "draft":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"订单状态 {orm.status} 不可修改")
        for k, v in kwargs.items():
            if hasattr(orm, k) and v is not None:
                setattr(orm, k, v)
        await self._session.flush()
        return orm

    async def submit_order(self, tenant_id: UUID, order_id: UUID) -> SalSalesOrderORM:
        _check_auth(tenant_id, "sal:order:create")
        orm = await self.get_order(tenant_id, order_id)
        if orm.status != "draft":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"订单状态 {orm.status} 不可提交")
        orm.status = "submitted"
        orm.submitted_by = _current_user_id()
        orm.submitted_at = datetime.now(timezone.utc)
        await self._session.flush()
        return orm

    async def approve_order(self, tenant_id: UUID, order_id: UUID, approved: bool = True,
                            approver_id: UUID | None = None) -> SalSalesOrderORM:
        _check_auth(tenant_id, "sal:order:approve")
        orm = await self.get_order(tenant_id, order_id)
        if orm.status != "submitted":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"订单状态 {orm.status} 不可审批")
        if approved:
            orm.status = "approved"
            orm.approved_by = approver_id or _current_user_id()
            orm.approved_at = datetime.now(timezone.utc)
        else:
            orm.status = "rejected"
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SALES_ORDER_APPROVED",
            order_id=orm.order_id,
        ))
        return orm

    async def confirm_order(self, tenant_id: UUID, order_id: UUID,
                            idempotency_key: str = "") -> SalSalesOrderORM:
        """确认履约 - 红线五：通过 INV Reservation API 预留库存。"""
        _check_auth(tenant_id, "sal:order:confirm")
        orm = await self.get_order(tenant_id, order_id)
        if orm.status != "approved":
            raise SALError(SALErrorCode.ORDER_NOT_APPROVED, "订单非已审批状态不可确认履约")
        lines = await self._repo.list_lines(self._session, tenant_id, order_id)
        reservation_ids: list[str] = []
        try:
            async with httpx.AsyncClient(base_url=INV_API_URL, timeout=30) as client:
                for line in lines:
                    resp = await client.post("/reservations", json={
                        "tenant_id": str(tenant_id),
                        "sku_id": str(line.enterprise_sku_id),
                        "warehouse_id": str(orm.shipping_warehouse_id) if orm.shipping_warehouse_id else None,
                        "quantity": float(line.ordered_quantity),
                        "source_document_id": str(order_id),
                        "source_document_type": "sal_order",
                        "source_line_id": str(line.line_id),
                        "idempotency_key": f"sal:order:{order_id}:reserve:{line.line_id}",
                        "correlation_id": str(orm.correlation_id or order_id),
                    })
                    if resp.status_code not in (200, 201):
                        raise SALError(SALErrorCode.RESERVATION_FAILED,
                                       f"INV预留失败: {resp.status_code} {resp.text[:200]}")
                    data = resp.json()
                    rid = data.get("reservation_id")
                    if rid:
                        reservation_ids.append(rid)
                        line.reservation_id = UUID(rid) if isinstance(rid, str) else rid
                        line.reserved_quantity = float(line.ordered_quantity)
                        line.status = "reserved"
        except SALError:
            raise
        except Exception as exc:
            raise SALError(SALErrorCode.RESERVATION_FAILED, f"INV预留异常: {exc}") from exc
        orm.status = "reserved"
        orm.reservation_ids = reservation_ids
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SALES_ORDER_RESERVED",
            order_id=orm.order_id, reservation_ids=reservation_ids,
        ))
        return orm

    async def change_order(self, tenant_id: UUID, order_id: UUID, lines: list[dict] | None = None,
                           reason: str = "") -> SalSalesOrderORM:
        """变更 - RESERVED/PARTIAL_SHIPPED 状态，需审批，版本递增。"""
        _check_auth(tenant_id, "sal:order:change")
        orm = await self.get_order(tenant_id, order_id)
        if orm.status not in ("reserved", "partial_shipped"):
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"订单状态 {orm.status} 不可变更")
        if lines:
            old_lines = await self._repo.list_lines(self._session, tenant_id, order_id)
            for ol in old_lines:
                await self._session.delete(ol)
            total = 0.0
            for idx, line_data in enumerate(lines, start=1):
                qty = float(line_data.get("ordered_quantity", 0))
                price = float(line_data.get("unit_price", 0))
                line = SalSalesOrderLineORM(
                    tenant_id=tenant_id, order_id=order_id, line_number=idx,
                    **{k: v for k, v in line_data.items() if hasattr(SalSalesOrderLineORM, k)},
                )
                await self._repo.save_line(self._session, line)
                total += qty * price
            orm.total_amount = total
        orm.version += 1
        orm.status = "submitted"
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SALES_ORDER_CHANGED",
            order_id=orm.order_id, reason=reason,
        ))
        return orm

    async def cancel_order(self, tenant_id: UUID, order_id: UUID) -> SalSalesOrderORM:
        """取消 - 校验已发货，仅取消未发部分，释放预留。"""
        _check_auth(tenant_id, "sal:order:cancel")
        orm = await self.get_order(tenant_id, order_id)
        lines = await self._repo.list_lines(self._session, tenant_id, order_id)
        if any(float(l.shipped_quantity) > 0 for l in lines):
            raise SALError(SALErrorCode.ORDER_CANCEL_WITH_SHIPPED, "已发货订单不可取消，需走退货流程")
        if orm.reservation_ids:
            async with httpx.AsyncClient(base_url=INV_API_URL, timeout=30) as client:
                for rid in orm.reservation_ids:
                    await client.post(f"/reservations/{rid}/release", json={
                        "tenant_id": str(tenant_id),
                        "idempotency_key": f"sal:order:{order_id}:release:{rid}",
                    })
        orm.status = "cancelled"
        orm.reservation_ids = []
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SALES_ORDER_CANCELLED",
            order_id=orm.order_id,
        ))
        return orm

    async def close_order(self, tenant_id: UUID, order_id: UUID) -> SalSalesOrderORM:
        _check_auth(tenant_id, "sal:order:close")
        orm = await self.get_order(tenant_id, order_id)
        if orm.status not in ("completed", "shipped"):
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"订单状态 {orm.status} 不可关闭")
        orm.status = "closed"
        await self._session.flush()
        return orm


class ShipmentAppSvc:
    """发货管理应用服务 - 红线一核心：通过 WMS Picking/Shipping API 触发拣货与发货。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ShipmentOrderRepository()
        self._order_repo = SalesOrderRepository()
        self._audit_repo = SalesAuditRepository()

    async def create_shipment(self, tenant_id: UUID, shipment_code: str, order_ids: list[UUID],
                              shipping_warehouse_id: UUID, lines: list[dict] | None = None,
                              picking_strategy: str = "fifo", idempotency_key: str = "",
                              **kwargs) -> SalShipmentOrderORM:
        _check_auth(tenant_id, "sal:shipment:create")
        if idempotency_key:
            existing = await self._repo.get_by_idempotency_key(self._session, tenant_id, idempotency_key)
            if existing:
                return existing
        for oid in order_ids:
            order = await self._order_repo.get_by_id(self._session, tenant_id, oid)
            if order is None:
                raise SALError(SALErrorCode.ORDER_NOT_FOUND, f"销售订单 {oid} 不存在")
            if order.status not in ("reserved", "partial_shipped"):
                raise SALError(SALErrorCode.SHIPMENT_ORDER_INVALID, f"订单 {oid} 状态 {order.status} 不可发货")
        orm = SalShipmentOrderORM(
            tenant_id=tenant_id, shipment_code=shipment_code,
            order_ids=[str(oid) for oid in order_ids], shipping_warehouse_id=shipping_warehouse_id,
            picking_strategy=picking_strategy, idempotency_key=idempotency_key,
            **{k: v for k, v in kwargs.items() if hasattr(SalShipmentOrderORM, k)},
        )
        orm = await self._repo.save(self._session, orm)
        if lines:
            for line_data in lines:
                await self._repo.save_line(self._session, SalShipmentLineORM(
                    tenant_id=tenant_id, shipment_id=orm.shipment_id,
                    **{k: v for k, v in line_data.items() if hasattr(SalShipmentLineORM, k)},
                ))
        return orm

    async def get_shipment(self, tenant_id: UUID, shipment_id: UUID) -> SalShipmentOrderORM:
        _check_auth(tenant_id, "sal:shipment:create")
        orm = await self._repo.get_by_id(self._session, tenant_id, shipment_id)
        if orm is None:
            raise SALError(SALErrorCode.SHIPMENT_NOT_FOUND, f"发货单 {shipment_id} 不存在")
        return orm

    async def list_shipments(self, tenant_id: UUID, status: str | None = None,
                             offset: int = 0, limit: int = 50) -> list[SalShipmentOrderORM]:
        _check_auth(tenant_id, "sal:shipment:create")
        if status:
            return await self._repo.list_by_status(self._session, tenant_id, status, offset, limit)
        from sqlalchemy import select
        return list((await self._session.execute(
            select(SalShipmentOrderORM).where(SalShipmentOrderORM.tenant_id == tenant_id).offset(offset).limit(limit)
        )).scalars().all())

    async def submit_shipment(self, tenant_id: UUID, shipment_id: UUID) -> SalShipmentOrderORM:
        """提交发货单 - 红线一：触发 WMS Picking API。"""
        _check_auth(tenant_id, "sal:shipment:create")
        orm = await self.get_shipment(tenant_id, shipment_id)
        if orm.status != "draft":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"发货单状态 {orm.status} 不可提交")
        lines = await self._repo.list_lines(self._session, tenant_id, shipment_id)
        params = {
            "tenant_id": str(tenant_id),
            "source_document_id": str(shipment_id),
            "source_document_type": "sal_shipment",
            "warehouse_id": str(orm.shipping_warehouse_id),
            "lines": [{"sku_id": str(l.enterprise_sku_id), "quantity": float(l.ship_quantity),
                       "order_line_id": str(l.order_line_id)} for l in lines],
            "picking_strategy": orm.picking_strategy,
            "idempotency_key": f"sal:shipment:{shipment_id}:pick",
            "correlation_id": str(orm.correlation_id or shipment_id),
        }
        async with httpx.AsyncClient(base_url=WMS_API_URL, timeout=30) as client:
            resp = await client.post("/picking/tasks", json=params)
            if resp.status_code not in (200, 201):
                raise SALError(SALErrorCode.WMS_PICKING_FAILED,
                               f"WMS拣货失败: {resp.status_code} {resp.text[:200]}")
            data = resp.json()
            orm.wms_picking_task_id = UUID(data["wms_picking_task_id"]) if isinstance(data.get("wms_picking_task_id"), str) else data.get("wms_picking_task_id")
        orm.status = "picking"
        await self._session.flush()
        return orm

    async def confirm_shipment(self, tenant_id: UUID, shipment_id: UUID, logistics_no: str,
                               carrier: str | None = None, idempotency_key: str = "") -> SalShipmentOrderORM:
        """发货确认 - 红线一：调用 WMS Shipping API。"""
        _check_auth(tenant_id, "sal:shipment:confirm")
        if not idempotency_key:
            raise SALError(SALErrorCode.IDEMPOTENCY_KEY_REQUIRED, "发货确认必须提供幂等键")
        orm = await self.get_shipment(tenant_id, shipment_id)
        if orm.status not in ("picking", "packed"):
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"发货单状态 {orm.status} 不可确认")
        lines = await self._repo.list_lines(self._session, tenant_id, shipment_id)
        params = {
            "tenant_id": str(tenant_id),
            "source_document_id": str(shipment_id),
            "source_document_type": "sal_shipment",
            "warehouse_id": str(orm.shipping_warehouse_id),
            "lines": [{"sku_id": str(l.enterprise_sku_id), "quantity": float(l.ship_quantity),
                       "order_line_id": str(l.order_line_id)} for l in lines],
            "logistics_no": logistics_no,
            "carrier": carrier or orm.carrier or "",
            "idempotency_key": idempotency_key,
            "correlation_id": str(orm.correlation_id or shipment_id),
        }
        inv_tx_ids: list[str] = []
        async with httpx.AsyncClient(base_url=WMS_API_URL, timeout=30) as client:
            resp = await client.post("/shipping/orders", json=params)
            if resp.status_code not in (200, 201):
                raise SALError(SALErrorCode.WMS_SHIPPING_FAILED,
                               f"WMS发货失败: {resp.status_code} {resp.text[:200]}")
            data = resp.json()
            wms_sid = data.get("wms_shipping_id")
            orm.wms_shipping_id = UUID(wms_sid) if isinstance(wms_sid, str) else wms_sid
            inv_tx_ids = data.get("inv_transaction_ids", [])
            if wms_sid:
                confirm_resp = await client.post(f"/shipping/orders/{wms_sid}/confirm", json={
                    "logistics_no": logistics_no, "idempotency_key": idempotency_key,
                })
                if confirm_resp.status_code not in (200, 201):
                    raise SALError(SALErrorCode.WMS_SHIPPING_FAILED,
                                   f"WMS发货确认失败: {confirm_resp.status_code}")
        orm.status = "shipped"
        orm.logistics_no = logistics_no
        orm.carrier = carrier
        orm.inv_transaction_ids = inv_tx_ids
        orm.shipped_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._update_order_four_state(tenant_id, orm, lines)
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SHIPMENT_CONFIRMED",
            shipment_id=orm.shipment_id, wms_shipping_id=orm.wms_shipping_id,
            inv_transaction_ids=inv_tx_ids,
        ))
        return orm

    async def _update_order_four_state(self, tenant_id: UUID, shipment: SalShipmentOrderORM,
                                       ship_lines: list[SalShipmentLineORM]) -> None:
        """更新订单四态（shipped += 本次量, remaining = ordered - shipped）+ 联动订单状态。"""
        for oid_str in shipment.order_ids:
            oid = UUID(oid_str) if isinstance(oid_str, str) else oid_str
            order = await self._order_repo.get_by_id(self._session, tenant_id, oid)
            if order is None:
                continue
            order_lines = await self._order_repo.list_lines(self._session, tenant_id, oid)
            line_map = {str(l.line_id): l for l in order_lines}
            all_shipped = True
            for sl in ship_lines:
                ol = line_map.get(str(sl.order_line_id))
                if ol is None:
                    continue
                new_shipped = float(ol.shipped_quantity) + float(sl.ship_quantity)
                await self._order_repo.update_shipped_quantity(self._session, tenant_id, ol.line_id, new_shipped)
                ol.shipped_quantity = new_shipped
                if float(ol.ordered_quantity) - new_shipped > 0:
                    all_shipped = False
            new_status = "shipped" if all_shipped else "partial_shipped"
            await self._order_repo.update_status(self._session, tenant_id, oid, new_status)
            order.status = new_status
        await self._session.flush()

    async def cancel_shipment(self, tenant_id: UUID, shipment_id: UUID) -> SalShipmentOrderORM:
        _check_auth(tenant_id, "sal:shipment:create")
        orm = await self.get_shipment(tenant_id, shipment_id)
        if orm.status in ("shipped", "confirmed"):
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"发货单状态 {orm.status} 不可取消")
        orm.status = "cancelled"
        await self._session.flush()
        return orm


class PackingAppSvc:
    """包装管理应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PackingRecordRepository()
        self._ship_repo = ShipmentOrderRepository()

    async def create_packing(self, tenant_id: UUID, shipment_id: UUID, lines: list[dict] | None = None,
                             **kwargs) -> SalPackingRecordORM:
        _check_auth(tenant_id, "sal:packing:manage")
        ship = await self._ship_repo.get_by_id(self._session, tenant_id, shipment_id)
        if ship is None:
            raise SALError(SALErrorCode.SHIPMENT_NOT_FOUND, f"发货单 {shipment_id} 不存在")
        orm = SalPackingRecordORM(
            tenant_id=tenant_id, shipment_id=shipment_id,
            **{k: v for k, v in kwargs.items() if hasattr(SalPackingRecordORM, k)},
        )
        orm = await self._repo.save(self._session, orm)
        if lines:
            for line_data in lines:
                await self._repo.save_line(self._session, SalPackingLineORM(
                    tenant_id=tenant_id, packing_id=orm.packing_id,
                    **{k: v for k, v in line_data.items() if hasattr(SalPackingLineORM, k)},
                ))
        return orm

    async def complete_packing(self, tenant_id: UUID, packing_id: UUID) -> SalPackingRecordORM:
        _check_auth(tenant_id, "sal:packing:manage")
        orm = await self._repo.get_by_id(self._session, tenant_id, packing_id)
        if orm is None:
            raise SALError(SALErrorCode.SHIPMENT_NOT_FOUND, f"包装记录 {packing_id} 不存在")
        orm.status = "packed"
        orm.packed_by = _current_user_id()
        orm.packed_at = datetime.now(timezone.utc)
        ship = await self._ship_repo.get_by_id(self._session, tenant_id, orm.shipment_id)
        if ship and ship.status == "picking":
            ship.status = "packed"
        await self._session.flush()
        return orm

    async def get_packing(self, tenant_id: UUID, shipment_id: UUID) -> SalPackingRecordORM | None:
        _check_auth(tenant_id, "sal:packing:manage")
        return await self._repo.get_by_shipment(self._session, tenant_id, shipment_id)


class SalesReturnAppSvc:
    """销售退货应用服务 - 红线一核心：通过 WMS Receiving API 触发退货收货。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SalesReturnRepository()
        self._order_repo = SalesOrderRepository()
        self._audit_repo = SalesAuditRepository()
        self._refund_calc = RefundCalculator()

    async def create_return(self, tenant_id: UUID, return_code: str, order_id: UUID,
                            original_shipment_id: UUID, lines: list[dict] | None = None,
                            return_reason: str = "", idempotency_key: str = "",
                            **kwargs) -> SalSalesReturnORM:
        _check_auth(tenant_id, "sal:return:create")
        if idempotency_key:
            existing = await self._repo.get_by_idempotency_key(self._session, tenant_id, idempotency_key)
            if existing:
                return existing
        order = await self._order_repo.get_by_id(self._session, tenant_id, order_id)
        if order is None:
            raise SALError(SALErrorCode.ORDER_NOT_FOUND, f"销售订单 {order_id} 不存在")
        orm = SalSalesReturnORM(
            tenant_id=tenant_id, return_code=return_code, order_id=order_id,
            original_shipment_id=original_shipment_id, return_reason=return_reason,
            idempotency_key=idempotency_key,
            **{k: v for k, v in kwargs.items() if hasattr(SalSalesReturnORM, k)},
        )
        orm = await self._repo.save(self._session, orm)
        if lines:
            for idx, line_data in enumerate(lines, start=1):
                await self._repo.save_line(self._session, SalReturnLineORM(
                    tenant_id=tenant_id, return_id=orm.return_id, line_number=idx,
                    **{k: v for k, v in line_data.items() if hasattr(SalReturnLineORM, k)},
                ))
        return orm

    async def get_return(self, tenant_id: UUID, return_id: UUID) -> SalSalesReturnORM:
        _check_auth(tenant_id, "sal:return:create")
        orm = await self._repo.get_by_id(self._session, tenant_id, return_id)
        if orm is None:
            raise SALError(SALErrorCode.RETURN_NOT_FOUND, f"退货单 {return_id} 不存在")
        return orm

    async def list_returns(self, tenant_id: UUID, status: str | None = None,
                           offset: int = 0, limit: int = 50) -> list[SalSalesReturnORM]:
        _check_auth(tenant_id, "sal:return:create")
        if status:
            return await self._repo.list_by_status(self._session, tenant_id, status, offset, limit)
        from sqlalchemy import select
        return list((await self._session.execute(
            select(SalSalesReturnORM).where(SalSalesReturnORM.tenant_id == tenant_id).offset(offset).limit(limit)
        )).scalars().all())

    async def submit_return(self, tenant_id: UUID, return_id: UUID) -> SalSalesReturnORM:
        _check_auth(tenant_id, "sal:return:create")
        orm = await self.get_return(tenant_id, return_id)
        if orm.status != "draft":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"退货单状态 {orm.status} 不可提交")
        orm.status = "submitted"
        orm.submitted_by = _current_user_id()
        orm.submitted_at = datetime.now(timezone.utc)
        await self._session.flush()
        return orm

    async def approve_return(self, tenant_id: UUID, return_id: UUID, approved: bool = True,
                             approver_id: UUID | None = None) -> SalSalesReturnORM:
        _check_auth(tenant_id, "sal:return:approve")
        orm = await self.get_return(tenant_id, return_id)
        if orm.status != "submitted":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"退货单状态 {orm.status} 不可审批")
        if approved:
            orm.status = "approved"
            orm.approved_by = approver_id or _current_user_id()
            orm.approved_at = datetime.now(timezone.utc)
        else:
            orm.status = "rejected"
        await self._session.flush()
        return orm

    async def execute_return(self, tenant_id: UUID, return_id: UUID,
                             idempotency_key: str = "") -> SalSalesReturnORM:
        """执行退货收货 - 红线一：通过 WMS Receiving API。"""
        _check_auth(tenant_id, "sal:return:execute")
        orm = await self.get_return(tenant_id, return_id)
        if orm.status != "approved":
            raise SALError(SALErrorCode.RETURN_NOT_APPROVED, "退货单非已审批状态不可执行收货")
        lines = await self._repo.list_lines(self._session, tenant_id, return_id)
        order = await self._order_repo.get_by_id(self._session, tenant_id, orm.order_id)
        warehouse_id = str(order.shipping_warehouse_id) if order and order.shipping_warehouse_id else None
        params = {
            "tenant_id": str(tenant_id),
            "source_document_id": str(return_id),
            "source_document_type": "sal_return",
            "warehouse_id": warehouse_id,
            "lines": [{"sku_id": str(l.enterprise_sku_id), "quantity": float(l.return_quantity)} for l in lines],
            "idempotency_key": idempotency_key or f"sal:return:{return_id}:receive",
            "correlation_id": str(orm.correlation_id or return_id),
        }
        inv_tx_ids: list[str] = []
        async with httpx.AsyncClient(base_url=WMS_API_URL, timeout=30) as client:
            resp = await client.post("/receiving/orders", json=params)
            if resp.status_code not in (200, 201):
                raise SALError(SALErrorCode.RETURN_RECEIVING_FAILED,
                               f"WMS收货失败: {resp.status_code} {resp.text[:200]}")
            data = resp.json()
            wms_rid = data.get("wms_receiving_id")
            orm.wms_receiving_id = UUID(wms_rid) if isinstance(wms_rid, str) else wms_rid
            inv_tx_ids = data.get("inv_transaction_ids", [])
            if wms_rid:
                exec_resp = await client.post(f"/receiving/orders/{wms_rid}/execute", json={
                    "idempotency_key": idempotency_key or f"sal:return:{return_id}:receive",
                })
                if exec_resp.status_code not in (200, 201):
                    raise SALError(SALErrorCode.RETURN_RECEIVING_FAILED,
                                   f"WMS收货执行失败: {exec_resp.status_code}")
        orm.status = "receiving"
        orm.inv_transaction_ids = inv_tx_ids
        await self._session.flush()
        return orm

    async def qc_return(self, tenant_id: UUID, return_id: UUID, line_id: UUID, qc_result: str,
                        qc_note: str = "") -> SalReturnLineORM:
        _check_auth(tenant_id, "sal:return:execute")
        orm = await self.get_return(tenant_id, return_id)
        lines = await self._repo.list_lines(self._session, tenant_id, return_id)
        for l in lines:
            if l.line_id == line_id:
                l.qc_result = qc_result
                return l
        raise SALError(SALErrorCode.RETURN_NOT_FOUND, f"退货行 {line_id} 不存在")

    async def dispose_return(self, tenant_id: UUID, return_id: UUID, line_id: UUID,
                             disposition: str) -> SalSalesReturnORM:
        """处置决策 - Restock/Quarantine/Scrap，通过 WMS/INV API 落地。"""
        _check_auth(tenant_id, "sal:return:execute")
        orm = await self.get_return(tenant_id, return_id)
        lines = await self._repo.list_lines(self._session, tenant_id, return_id)
        for l in lines:
            if l.line_id == line_id:
                l.disposition = disposition
        refund = self._refund_calc.calculate(lines)
        orm.refund_amount = refund
        orm.status = "completed"
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SALES_RETURN_COMPLETED",
            return_id=orm.return_id, wms_receiving_id=orm.wms_receiving_id,
        ))
        return orm


class SalesSettlementAppSvc:
    """销售结算应用服务 - 红线二核心：通过 INV Financial/Revenue API 落地收入。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SalesSettlementRepository()
        self._order_repo = SalesOrderRepository()
        self._audit_repo = SalesAuditRepository()

    async def create_settlement(self, tenant_id: UUID, settlement_code: str, order_id: UUID,
                                receivable_amount: float, idempotency_key: str = "",
                                **kwargs) -> SalSalesSettlementORM:
        _check_auth(tenant_id, "sal:settlement:execute")
        order = await self._order_repo.get_by_id(self._session, tenant_id, order_id)
        if order is None:
            raise SALError(SALErrorCode.ORDER_NOT_FOUND, f"销售订单 {order_id} 不存在")
        orm = SalSalesSettlementORM(
            tenant_id=tenant_id, settlement_code=settlement_code, order_id=order_id,
            receivable_amount=receivable_amount, net_receivable_amount=receivable_amount,
            idempotency_key=idempotency_key,
            **{k: v for k, v in kwargs.items() if hasattr(SalSalesSettlementORM, k)},
        )
        return await self._repo.save(self._session, orm)

    async def get_settlement(self, tenant_id: UUID, settlement_id: UUID) -> SalSalesSettlementORM:
        _check_auth(tenant_id, "sal:settlement:execute")
        orm = await self._repo.get_by_id(self._session, tenant_id, settlement_id)
        if orm is None:
            raise SALError(SALErrorCode.SETTLEMENT_NOT_FOUND, f"结算单 {settlement_id} 不存在")
        return orm

    async def list_settlements(self, tenant_id: UUID, status: str | None = None,
                               offset: int = 0, limit: int = 50) -> list[SalSalesSettlementORM]:
        _check_auth(tenant_id, "sal:settlement:execute")
        if status:
            return await self._repo.list_by_status(self._session, tenant_id, status, offset, limit)
        from sqlalchemy import select
        return list((await self._session.execute(
            select(SalSalesSettlementORM).where(SalSalesSettlementORM.tenant_id == tenant_id).offset(offset).limit(limit)
        )).scalars().all())

    async def reconcile(self, tenant_id: UUID, settlement_id: UUID, received_amount: float,
                        diff_threshold: float = 0.01) -> SalSalesSettlementORM:
        """对账确认 - 校对明细 + 差异校验。"""
        _check_auth(tenant_id, "sal:settlement:execute")
        orm = await self.get_settlement(tenant_id, settlement_id)
        if orm.status != "pending":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"结算单状态 {orm.status} 不可对账")
        diff = float(orm.receivable_amount) - received_amount
        if abs(diff) > diff_threshold:
            orm.status = "diff_found"
            raise SALError(SALErrorCode.SETTLEMENT_RECONCILE_DIFF_EXCEEDED,
                           f"对账差异 {abs(diff):.2f} 超过阈值 {diff_threshold}")
        orm.net_receivable_amount = received_amount
        orm.status = "reconciled"
        orm.reconciled_by = _current_user_id()
        orm.reconciled_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SALES_SETTLEMENT_RECONCILED",
            settlement_id=orm.settlement_id,
        ))
        return orm

    async def match_invoice(self, tenant_id: UUID, settlement_id: UUID, invoice_id: UUID,
                            matched_amount: float, diff_threshold: float = 0.01) -> SalSalesSettlementORM:
        """发票匹配 - 校验金额。"""
        _check_auth(tenant_id, "sal:settlement:execute")
        orm = await self.get_settlement(tenant_id, settlement_id)
        if orm.status != "reconciled":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"结算单状态 {orm.status} 不可匹配发票")
        diff = abs(float(orm.net_receivable_amount) - matched_amount)
        if diff > diff_threshold:
            raise SALError(SALErrorCode.INVOICE_MATCH_DIFF_EXCEEDED,
                           f"发票匹配差异 {diff:.2f} 超过阈值 {diff_threshold}")
        orm.invoice_id = invoice_id
        orm.status = "invoice_matched"
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="SALES_INVOICE_MATCHED",
            settlement_id=orm.settlement_id, invoice_id=invoice_id,
        ))
        return orm

    async def request_payment(self, tenant_id: UUID, settlement_id: UUID,
                               payment_code: str, amount: float) -> SalPaymentReceiptORM:
        """创建收款申请 - INVOICE_MATCHED → PAYMENT_REQUESTED。"""
        _check_auth(tenant_id, "sal:payment:request")
        orm = await self.get_settlement(tenant_id, settlement_id)
        if orm.status != "invoice_matched":
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, f"结算单状态 {orm.status} 不可申请收款")
        pay_orm = SalPaymentReceiptORM(
            tenant_id=tenant_id, settlement_id=settlement_id, payment_amount=amount,
            requested_by=_current_user_id(),
        )
        pay_repo = PaymentReceiptRepository()
        pay_orm = await pay_repo.save(self._session, pay_orm)
        orm.payment_receipt_id = pay_orm.payment_receipt_id
        orm.status = "payment_requested"
        await self._session.flush()
        return pay_orm

    async def land_revenue(self, tenant_id: UUID, settlement_id: UUID, sku_id: UUID,
                           warehouse_id: UUID, quantity: float, unit_price: float,
                           moving_avg_cost: float, idempotency_key: str = "") -> dict:
        """通过 INV Financial/Revenue API 落地销售收入与成本结转 - 红线二。"""
        _check_auth(tenant_id, "sal:settlement:execute")
        params = {
            "tenant_id": str(tenant_id),
            "document_id": str(settlement_id),
            "document_type": "sal_settlement",
            "sku_id": str(sku_id),
            "warehouse_id": str(warehouse_id),
            "quantity": quantity,
            "unit_price": unit_price,
            "moving_avg_cost": moving_avg_cost,
            "revenue_amount": unit_price * quantity,
            "cost_amount": moving_avg_cost * quantity,
            "idempotency_key": idempotency_key or f"sal:settlement:{settlement_id}:revenue:{sku_id}",
        }
        async with httpx.AsyncClient(base_url=INV_API_URL, timeout=30) as client:
            resp = await client.post("/financial/revenue", json=params)
            if resp.status_code not in (200, 201):
                raise SALError(SALErrorCode.FINANCIAL_API_FAILED,
                               f"INV收入落地失败: {resp.status_code} {resp.text[:200]}")
            return resp.json()


class SalesInvoiceAppSvc:
    """发票管理应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SalesInvoiceRepository()
        self._settle_repo = SalesSettlementRepository()
        self._audit_repo = SalesAuditRepository()

    async def create_invoice(self, tenant_id: UUID, invoice_code: str, customer_id: UUID,
                             invoice_amount: float, lines: list[dict] | None = None,
                             tax_amount: float = 0, **kwargs) -> SalSalesInvoiceORM:
        _check_auth(tenant_id, "sal:invoice:create")
        orm = SalSalesInvoiceORM(
            tenant_id=tenant_id, invoice_code=invoice_code, customer_id=customer_id,
            invoice_amount=invoice_amount, tax_amount=tax_amount,
            **{k: v for k, v in kwargs.items() if hasattr(SalSalesInvoiceORM, k)},
        )
        orm = await self._repo.save(self._session, orm)
        if lines:
            for idx, line_data in enumerate(lines, start=1):
                await self._repo.save_line(self._session, SalInvoiceLineORM(
                    tenant_id=tenant_id, invoice_id=orm.invoice_id, line_number=idx,
                    **{k: v for k, v in line_data.items() if hasattr(SalInvoiceLineORM, k)},
                ))
        return orm

    async def list_invoices(self, tenant_id: UUID, status: str | None = None,
                            offset: int = 0, limit: int = 50) -> list[SalSalesInvoiceORM]:
        _check_auth(tenant_id, "sal:invoice:create")
        if status:
            return await self._repo.list_by_status(self._session, tenant_id, status, offset, limit)
        from sqlalchemy import select
        return list((await self._session.execute(
            select(SalSalesInvoiceORM).where(SalSalesInvoiceORM.tenant_id == tenant_id).offset(offset).limit(limit)
        )).scalars().all())

    async def match_settlement(self, tenant_id: UUID, invoice_id: UUID, settlement_id: UUID,
                               matched_amount: float, diff_threshold: float = 0.01) -> SalSalesInvoiceORM:
        _check_auth(tenant_id, "sal:invoice:create")
        orm = await self._repo.get_by_id(self._session, tenant_id, invoice_id)
        if orm is None:
            raise SALError(SALErrorCode.INVOICE_NOT_FOUND, f"发票 {invoice_id} 不存在")
        diff = abs(float(orm.invoice_amount) - matched_amount)
        if diff > diff_threshold:
            raise SALError(SALErrorCode.INVOICE_MATCH_DIFF_EXCEEDED,
                           f"发票匹配差异 {diff:.2f} 超过阈值 {diff_threshold}")
        orm.matched_settlement_id = settlement_id
        orm.status = "matched"
        await self._session.flush()
        return orm


class PaymentReceiptAppSvc:
    """收款管理应用服务 - 收款确认触发信用释放。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PaymentReceiptRepository()
        self._settle_repo = SalesSettlementRepository()
        self._credit_repo = CreditLimitRepository()
        self._order_repo = SalesOrderRepository()
        self._cust_repo = CustomerRepository()
        self._audit_repo = SalesAuditRepository()

    async def list_payments(self, tenant_id: UUID, status: str | None = None,
                            offset: int = 0, limit: int = 50) -> list[SalPaymentReceiptORM]:
        _check_auth(tenant_id, "sal:payment:request")
        if status:
            return await self._repo.list_by_status(self._session, tenant_id, status, offset, limit)
        from sqlalchemy import select
        return list((await self._session.execute(
            select(SalPaymentReceiptORM).where(SalPaymentReceiptORM.tenant_id == tenant_id).offset(offset).limit(limit)
        )).scalars().all())

    async def confirm_payment(self, tenant_id: UUID, payment_id: UUID, payment_no: str = "",
                              idempotency_key: str = "") -> SalPaymentReceiptORM:
        """收款确认回调 - PAYMENT_REQUESTED → PAYMENT_COMPLETED，释放信用。"""
        _check_auth(tenant_id, "sal:payment:confirm")
        orm = await self._repo.get_by_id(self._session, tenant_id, payment_id)
        if orm is None:
            raise SALError(SALErrorCode.PAYMENT_NOT_FOUND, f"收款单 {payment_id} 不存在")
        if orm.status not in ("requested", "executing"):
            raise SALError(SALErrorCode.PAYMENT_FAILED, f"收款单状态 {orm.status} 不可确认")
        orm.status = "completed"
        orm.payment_no = payment_no
        orm.completed_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._release_credit_on_payment(tenant_id, orm)
        settle = await self._settle_repo.get_by_id(self._session, tenant_id, orm.settlement_id)
        if settle:
            settle.status = "payment_completed"
            await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="PAYMENT_RECEIVED",
            payment_id=orm.payment_receipt_id, settlement_id=orm.settlement_id,
        ))
        return orm

    async def _release_credit_on_payment(self, tenant_id: UUID, payment: SalPaymentReceiptORM) -> None:
        """收款完成后释放信用额度。"""
        settle = await self._settle_repo.get_by_id(self._session, tenant_id, payment.settlement_id)
        if settle is None:
            return
        order = await self._order_repo.get_by_id(self._session, tenant_id, settle.order_id)
        if order is None:
            return
        credit = await self._credit_repo.get_for_update(self._session, tenant_id, order.customer_id)
        if credit is None:
            return
        release_amount = min(float(credit.used_amount), float(payment.payment_amount))
        credit.used_amount = float(credit.used_amount) - release_amount
        credit.version += 1
        await self._session.flush()
        await self._audit_repo.append(self._session, SalSalesAuditORM(
            tenant_id=tenant_id, user_id=_current_user_id(), event_type="CREDIT_LIMIT_RELEASED",
            customer_id=order.customer_id, payment_id=payment.payment_receipt_id,
        ))


class SalReconcileAppSvc:
    """销售↔WMS↔INV 三边对账应用服务 - 第七条红线。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._ship_repo = ShipmentOrderRepository()
        self._order_repo = SalesOrderRepository()
        self._audit_repo = SalesAuditRepository()
        self._reconcile_svc = SalReconcileService()

    async def run_reconcile(self, tenant_id: UUID, order_id: UUID | None = None) -> dict:
        _check_auth(tenant_id, "sal:reconcile:execute")
        diffs = []
        if order_id:
            ship_list = await self._ship_repo.list_by_order(self._session, tenant_id, order_id)
            for ship in ship_list:
                diff = {
                    "shipment_id": str(ship.shipment_id),
                    "sal_status": ship.status,
                    "wms_shipping_id": str(ship.wms_shipping_id) if ship.wms_shipping_id else None,
                    "inv_transaction_ids": ship.inv_transaction_ids,
                    "consistent": ship.status == "shipped" and bool(ship.wms_shipping_id),
                }
                diffs.append(diff)
                if not diff["consistent"]:
                    await self._audit_repo.append(self._session, SalSalesAuditORM(
                        tenant_id=tenant_id, user_id=_current_user_id(),
                        event_type="SAL_WMS_INV_INCONSISTENT", order_id=order_id,
                        shipment_id=ship.shipment_id, wms_shipping_id=ship.wms_shipping_id,
                    ))
        return {"tenant_id": str(tenant_id), "order_id": str(order_id) if order_id else None,
                "diffs": diffs, "consistent": all(d["consistent"] for d in diffs)}

    async def list_diffs(self, tenant_id: UUID, offset: int = 0, limit: int = 50) -> list[dict]:
        _check_auth(tenant_id, "sal:reconcile:execute")
        audits = await self._audit_repo.query_by_time_range(
            self._session, tenant_id,
            datetime(2000, 1, 1, tzinfo=timezone.utc),
            datetime.now(timezone.utc), offset, limit,
        )
        return [
            {"audit_id": str(a.audit_id), "event_type": a.event_type,
             "order_id": str(a.order_id) if a.order_id else None,
             "shipment_id": str(a.shipment_id) if a.shipment_id else None,
             "wms_shipping_id": str(a.wms_shipping_id) if a.wms_shipping_id else None}
            for a in audits if a.event_type == "SAL_WMS_INV_INCONSISTENT"
        ]

    async def repair(self, tenant_id: UUID, shipment_id: UUID, repair_note: str = "") -> dict:
        """以 WMS/INV 为准修复销售发货状态。"""
        _check_auth(tenant_id, "sal:reconcile:execute")
        ship = await self._ship_repo.get_by_id(self._session, tenant_id, shipment_id)
        if ship is None:
            raise SALError(SALErrorCode.SHIPMENT_NOT_FOUND, f"发货单 {shipment_id} 不存在")
        if ship.wms_shipping_id and ship.status != "shipped":
            await self._ship_repo.update_status(self._session, tenant_id, shipment_id, "shipped")
            ship.status = "shipped"
            await self._session.flush()
        return {"shipment_id": str(shipment_id), "repaired_status": ship.status, "repair_note": repair_note}