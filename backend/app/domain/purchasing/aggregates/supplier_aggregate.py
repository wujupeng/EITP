"""PUR SupplierAggregate 聚合根 - 供应商档案，含治理工作流状态 + 银行账户脱敏。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.purchasing.entities.supplier_scope import SupplierScope
from app.domain.purchasing.value_objects.supplier_vo import (
    Address,
    BankAccount,
    ContactInfo,
    SupplierStatus,
    SupplierType,
)
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


_VALID_TRANSITIONS: dict[SupplierStatus, set[SupplierStatus]] = {
    SupplierStatus.DRAFT: {SupplierStatus.SUBMITTED, SupplierStatus.CANCELLED},
    SupplierStatus.SUBMITTED: {SupplierStatus.APPROVED, SupplierStatus.REJECTED},
    SupplierStatus.APPROVED: {SupplierStatus.ACTIVE},
    SupplierStatus.ACTIVE: {SupplierStatus.DISABLED},
    SupplierStatus.DISABLED: {SupplierStatus.ACTIVE},
    SupplierStatus.REJECTED: set(),
    SupplierStatus.CANCELLED: set(),
}


@dataclass
class SupplierAggregate:
    """供应商聚合根 - 禁止贫血模型。"""

    supplier_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    supplier_code: str = ""
    supplier_name: str = ""
    supplier_type: SupplierType = SupplierType.DISTRIBUTOR
    tax_id: str = ""
    contact_info: ContactInfo = field(default_factory=ContactInfo)
    address: Address = field(default_factory=Address)
    bank_account: BankAccount = field(default_factory=BankAccount)
    status: SupplierStatus = SupplierStatus.DRAFT
    published_version: int = 0
    governance_state: str = "draft"
    scopes: list[SupplierScope] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: SupplierStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise PURError(
                PURErrorCode.ORDER_INVALID_STATE_TRANSITION,
                f"供应商状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def submit(self) -> None:
        self._transition(SupplierStatus.SUBMITTED)
        self.governance_state = "submitted"

    def approve(self, approver_id: UUID, opinion: str = "") -> None:
        self._transition(SupplierStatus.APPROVED)
        self.governance_state = "approved"

    def reject(self, approver_id: UUID, opinion: str = "") -> None:
        self._transition(SupplierStatus.REJECTED)
        self.governance_state = "rejected"

    def publish(self) -> None:
        self._transition(SupplierStatus.ACTIVE)
        self.published_version += 1
        self.governance_state = "published"

    def disable(self) -> None:
        self._transition(SupplierStatus.DISABLED)

    def cancel(self) -> None:
        self._transition(SupplierStatus.CANCELLED)

    def add_scope(self, scope: SupplierScope) -> None:
        if self.status != SupplierStatus.ACTIVE:
            raise PURError(PURErrorCode.SUPPLIER_NOT_ACTIVE, "仅 ACTIVE 状态供应商可添加供货范围")
        existing = next((s for s in self.scopes if s.enterprise_sku_id == scope.enterprise_sku_id), None)
        if existing is not None:
            raise PURError(PURErrorCode.SUPPLIER_SCOPE_MISMATCH, "供货范围已存在")
        self.scopes.append(scope)

    def update_scope(self, scope_id: UUID, **kwargs) -> None:
        scope = next((s for s in self.scopes if s.scope_id == scope_id), None)
        if scope is None:
            raise PURError(PURErrorCode.SUPPLIER_SCOPE_MISMATCH, "供货范围不存在")
        for key, value in kwargs.items():
            if hasattr(scope, key):
                setattr(scope, key, value)

    @property
    def is_active(self) -> bool:
        return self.status == SupplierStatus.ACTIVE

    @property
    def can_receive_orders(self) -> bool:
        return self.status == SupplierStatus.ACTIVE