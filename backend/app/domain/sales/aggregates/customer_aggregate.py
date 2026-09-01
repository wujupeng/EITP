"""SAL CustomerAggregate 聚合根 - 客户档案，含治理工作流 + 银行账户脱敏 + 多地址 + 多联系人。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.entities.customer_address import CustomerAddress
from app.domain.sales.entities.customer_contact import CustomerContact
from app.domain.sales.value_objects.customer_vo import (
    BankAccount,
    ContactInfo,
    CustomerStatus,
    CustomerType,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode

_VALID_TRANSITIONS: dict[CustomerStatus, set[CustomerStatus]] = {
    CustomerStatus.DRAFT: {CustomerStatus.SUBMITTED, CustomerStatus.CANCELLED},
    CustomerStatus.SUBMITTED: {
        CustomerStatus.APPROVED,
        CustomerStatus.REJECTED,
        CustomerStatus.CANCELLED,
    },
    CustomerStatus.APPROVED: {CustomerStatus.ACTIVE},
    CustomerStatus.ACTIVE: {CustomerStatus.DISABLED},
    CustomerStatus.DISABLED: {CustomerStatus.ACTIVE},
    CustomerStatus.REJECTED: set(),
    CustomerStatus.CANCELLED: set(),
}


@dataclass
class CustomerAggregate:
    """客户聚合根 - 禁止贫血模型。

    状态机：DRAFT→SUBMITTED→APPROVED→ACTIVE→DISABLED，可 REJECTED/CANCELLED。
    仅 ACTIVE 状态客户可用于销售订单。
    """

    customer_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    customer_code: str = ""
    customer_name: str = ""
    customer_type: CustomerType = CustomerType.CORPORATE
    tax_id: str = ""
    contact_info: ContactInfo = field(default_factory=ContactInfo)
    bank_account: BankAccount = field(default_factory=BankAccount)
    category_ids: list[UUID] = field(default_factory=list)
    status: CustomerStatus = CustomerStatus.DRAFT
    published_version: int = 0
    governance_state: str = "draft"
    addresses: list[CustomerAddress] = field(default_factory=list)
    contacts: list[CustomerContact] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: CustomerStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise SALError(
                SALErrorCode.ORDER_INVALID_STATE_TRANSITION,
                f"客户状态非法流转: {self.status.value} → {target.value}",
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def submit(self) -> None:
        """DRAFT→SUBMITTED：提交审批。"""
        if not self.customer_code or not self.customer_name:
            raise SALError(SALErrorCode.CUSTOMER_NOT_FOUND, "客户编码或名称缺失")
        self._transition(CustomerStatus.SUBMITTED)
        self.governance_state = "submitted"

    def approve(self, approver_id: UUID, opinion: str = "") -> None:
        """SUBMITTED→APPROVED：审批通过，复用 MDM GovernanceWorkflow。"""
        self._transition(CustomerStatus.APPROVED)
        self.governance_state = "approved"

    def reject(self, approver_id: UUID, opinion: str = "") -> None:
        """SUBMITTED→REJECTED：审批拒绝。"""
        self._transition(CustomerStatus.REJECTED)
        self.governance_state = "rejected"

    def publish(self) -> None:
        """APPROVED→ACTIVE：发布生效，published_version 递增。"""
        self._transition(CustomerStatus.ACTIVE)
        self.published_version += 1
        self.governance_state = "published"

    def disable(self) -> None:
        """ACTIVE→DISABLED：停用，保留存量订单但拒绝新订单。"""
        self._transition(CustomerStatus.DISABLED)

    def enable(self) -> None:
        """DISABLED→ACTIVE：重新启用。"""
        self._transition(CustomerStatus.ACTIVE)

    def cancel(self) -> None:
        """DRAFT/SUBMITTED→CANCELLED：取消。"""
        self._transition(CustomerStatus.CANCELLED)

    def add_address(self, address: CustomerAddress) -> None:
        """添加地址。"""
        address.customer_id = self.customer_id
        self.addresses.append(address)
        self.updated_at = datetime.now(timezone.utc)

    def add_contact(self, contact: CustomerContact) -> None:
        """添加联系人。"""
        contact.customer_id = self.customer_id
        self.contacts.append(contact)
        self.updated_at = datetime.now(timezone.utc)

    def assign_categories(self, category_ids: list[UUID]) -> None:
        """分配分类归属。"""
        self.category_ids = list(set(self.category_ids) | set(category_ids))
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_active(self) -> bool:
        return self.status == CustomerStatus.ACTIVE

    @property
    def can_receive_orders(self) -> bool:
        """仅 ACTIVE 状态客户可用于销售订单。"""
        return self.status == CustomerStatus.ACTIVE

    @property
    def default_address(self) -> CustomerAddress | None:
        return next((a for a in self.addresses if a.address_type.value == "default"), None)

    @property
    def shipping_address(self) -> CustomerAddress | None:
        return next((a for a in self.addresses if a.is_shipping), None)