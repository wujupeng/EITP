"""FIN 付款审批策略 - PaymentApprovalPolicy 分级审批。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.money import Money

FIN_MANAGER_ROLE = "FIN_MANAGER"
FIN_DIRECTOR_ROLE = "FIN_DIRECTOR"
DUAL_SIGN_ROLE = "DUAL_SIGN"

MANAGER_THRESHOLD = Decimal("50000")
DIRECTOR_THRESHOLD = Decimal("500000")


@dataclass(frozen=True)
class ApprovalRequirement:
    """审批要求 - 所需角色与是否双签。"""

    required_roles: tuple[str, ...]
    needs_dual_sign: bool


class PaymentApprovalPolicy:
    """付款分级审批策略 - ≤50000 财务主管 / 50000-500000 财务总监 / >500000 双签。"""

    @staticmethod
    def evaluate(amount: Money) -> ApprovalRequirement:
        value = amount.amount
        if value <= MANAGER_THRESHOLD:
            return ApprovalRequirement(
                required_roles=(FIN_MANAGER_ROLE,),
                needs_dual_sign=False,
            )
        if value <= DIRECTOR_THRESHOLD:
            return ApprovalRequirement(
                required_roles=(FIN_DIRECTOR_ROLE,),
                needs_dual_sign=False,
            )
        return ApprovalRequirement(
            required_roles=(FIN_DIRECTOR_ROLE, DUAL_SIGN_ROLE),
            needs_dual_sign=True,
        )

    @staticmethod
    def check_authority(amount: Money, approver_roles: list[str]) -> ApprovalRequirement:
        requirement = PaymentApprovalPolicy.evaluate(amount)
        missing = [r for r in requirement.required_roles if r not in approver_roles]
        if missing:
            raise FINError(
                FINErrorCode.PAYMENT_APPROVAL_EXCEED_AUTHORITY,
                f"payment amount {amount} requires roles {requirement.required_roles}, "
                f"approver missing {missing}",
            )
        return requirement