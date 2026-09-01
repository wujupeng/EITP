"""SAL SalesApprovalRouterService 领域服务 - 销售审批人路由（红线四）。

复用 MDM-001 GovernanceWorkflow 状态机模式，不重新实现审批引擎。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class DocumentType(str, Enum):
    CUSTOMER = "customer"
    QUOTATION = "quotation"
    ORDER = "order"
    RETURN = "return"
    PRICING = "pricing"


@dataclass(frozen=True)
class ApprovalRule:
    """审批路由规则。"""

    threshold: float
    approver_role: str


@dataclass(frozen=True)
class ApprovalRouteResult:
    """审批路由结果。"""

    approver_roles: list[str]
    document_type: DocumentType
    amount: float
    reason: str = ""


class SalesApprovalRouterService:
    """销售审批人路由服务。

    输入：(单据类型, 金额, 客户分类, 销售员)
    输出：审批人列表
    核心逻辑：按金额阈值路由（>10 万销售经理、>50 万总经理）
            + 按客户分类路由 + 按销售员权限路由。

    复用 MDM GovernanceWorkflow 状态机（红线四）。
    P1 扩展：按 SKU 分类路由，采用规则模式新增路由规则只需实现接口并注册。
    """

    def __init__(
        self,
        manager_threshold: float = 100000.0,
        director_threshold: float = 500000.0,
        extra_rules: list[ApprovalRule] | None = None,
    ) -> None:
        self._manager_threshold = manager_threshold
        self._director_threshold = director_threshold
        self._rules = sorted(
            extra_rules
            or [
                ApprovalRule(threshold=manager_threshold, approver_role="sal:approver_l1"),
                ApprovalRule(threshold=director_threshold, approver_role="sal:approver_l2"),
                ApprovalRule(threshold=float("inf"), approver_role="sal:approver_l3"),
            ],
            key=lambda r: r.threshold,
        )

    def route(
        self,
        document_type: DocumentType,
        amount: float,
        customer_category_ids: list[UUID] | None = None,
        sales_person_id: UUID | None = None,
    ) -> ApprovalRouteResult:
        """路由审批人 - 按金额阈值 + 客户分类 + 销售员权限。"""
        roles: list[str] = []
        reason_parts: list[str] = []

        # 1. 按金额阈值路由
        for rule in self._rules:
            if amount <= rule.threshold:
                roles.append(rule.approver_role)
                reason_parts.append(f"amount={amount} ≤ threshold={rule.threshold}")
                break
        else:
            roles.append(self._rules[-1].approver_role)
            reason_parts.append(f"amount={amount} > max_threshold")

        # 2. 按客户分类路由（VIP 客户需更高级审批）
        if customer_category_ids:
            roles.append("sal:approver_customer_category")
            reason_parts.append(f"customer_categories={len(customer_category_ids)}")

        # 3. 按销售员权限路由（销售员自身不可审批自己的单）
        if sales_person_id is not None:
            roles.append("sal:approver_peer_review")
            reason_parts.append("peer_review_required")

        # 去重保序
        seen: set[str] = set()
        unique_roles: list[str] = []
        for r in roles:
            if r not in seen:
                seen.add(r)
                unique_roles.append(r)

        return ApprovalRouteResult(
            approver_roles=unique_roles,
            document_type=document_type,
            amount=amount,
            reason="; ".join(reason_parts),
        )

    def route_by_amount(self, amount: float) -> str:
        """仅按金额阈值路由，返回单个审批人角色。"""
        for rule in self._rules:
            if amount <= rule.threshold:
                return rule.approver_role
        return self._rules[-1].approver_role