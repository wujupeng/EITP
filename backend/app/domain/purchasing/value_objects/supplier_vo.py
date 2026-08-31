"""PUR 供应商值对象 - SupplierType/SupplierStatus/ContactInfo/Address/BankAccount。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SupplierType(str, Enum):
    MANUFACTURER = "manufacturer"
    DISTRIBUTOR = "distributor"
    SERVICE_PROVIDER = "service_provider"
    INDIVIDUAL = "individual"


class SupplierStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    DISABLED = "disabled"
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
    bank_name: str = ""
    account_number_masked: str = ""
    branch: str = ""

    @classmethod
    def from_raw(cls, bank_name: str, account_number: str, branch: str = "") -> "BankAccount":
        if len(account_number) <= 4:
            masked = account_number
        else:
            masked = "*" * (len(account_number) - 4) + account_number[-4:]
        return cls(bank_name=bank_name, account_number_masked=masked, branch=branch)

    @property
    def last_four(self) -> str:
        return self.account_number_masked[-4:] if len(self.account_number_masked) >= 4 else self.account_number_masked