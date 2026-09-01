"""SAL 客户值对象 - CustomerType/CustomerStatus/ContactInfo/Address/BankAccount。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CustomerType(str, Enum):
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"
    DEALER = "dealer"
    RETAILER = "retailer"
    DISTRIBUTOR = "distributor"


class CustomerStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    ACTIVE = "active"
    DISABLED = "disabled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ContactInfo:
    name: str = ""
    phone: str = ""
    email: str = ""


@dataclass(frozen=True)
class Address:
    province: str = ""
    city: str = ""
    district: str = ""
    detail: str = ""


@dataclass(frozen=True)
class BankAccount:
    """银行账户值对象 - 脱敏存储，仅末 4 位明文。"""

    bank_name: str = ""
    account_number_masked: str = ""
    branch: str = ""

    @classmethod
    def from_raw(cls, bank_name: str, account_number: str, branch: str = "") -> BankAccount:
        if len(account_number) <= 4:
            masked = account_number
        else:
            masked = "*" * (len(account_number) - 4) + account_number[-4:]
        return cls(bank_name=bank_name, account_number_masked=masked, branch=branch)

    @property
    def last_four(self) -> str:
        masked = self.account_number_masked
        return masked[-4:] if len(masked) >= 4 else masked