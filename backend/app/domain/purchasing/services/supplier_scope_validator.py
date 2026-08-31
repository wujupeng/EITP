"""PUR SupplierScopeValidator 领域服务 - 供货范围校验。"""

from __future__ import annotations

from uuid import UUID

from app.domain.purchasing.aggregates.supplier_aggregate import SupplierAggregate
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class SupplierScopeValidator:
    """供货范围校验服务 - 输入(supplier, enterprise_sku_id)，输出bool。"""

    @staticmethod
    def validate(supplier: SupplierAggregate, enterprise_sku_id: UUID) -> bool:
        if not supplier.is_active:
            raise PURError(PURErrorCode.SUPPLIER_NOT_ACTIVE, "供应商非ACTIVE状态")
        scope = next(
            (s for s in supplier.scopes if s.enterprise_sku_id == enterprise_sku_id and s.is_active),
            None,
        )
        if scope is None:
            raise PURError(
                PURErrorCode.SUPPLIER_SCOPE_MISMATCH,
                "供应商供货范围不包含该SKU",
            )
        return True

    @staticmethod
    def get_agreement_price(supplier: SupplierAggregate, enterprise_sku_id: UUID) -> float | None:
        scope = next(
            (s for s in supplier.scopes if s.enterprise_sku_id == enterprise_sku_id and s.is_active),
            None,
        )
        return scope.agreement_price if scope else None