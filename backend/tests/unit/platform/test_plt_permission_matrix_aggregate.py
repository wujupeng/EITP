"""PLT PermissionMatrixAggregate / MenuTreeAggregate 单元测试 - 权限决策数据源。

覆盖 PermissionMatrixAggregate.create() 初始 PENDING、approve()/reject() 状态流转、
is_effective() 仅 APPROVED 为真；MenuTreeAggregate.create() 默认可见、hide()/show() 切换。
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.domain.platform.permission.aggregates.permission_matrix_aggregate import (
    ApprovalStatus,
    Decision,
    MenuTreeAggregate,
    PermissionMatrixAggregate,
)


class PermissionMatrixAggregateTest:
    """PermissionMatrixAggregate 审批状态机测试。"""

    def test_create_sets_approval_status_to_pending(self) -> None:
        matrix = PermissionMatrixAggregate.create(
            role_id="role-admin",
            operation="order:read",
            resource_scope="tenant",
            data_scope="self",
            decision=Decision.ALLOW,
            tenant_id=uuid4(),
        )
        assert matrix.approval_status == ApprovalStatus.PENDING
        assert matrix.approved_by is None
        assert matrix.version == 1
        assert matrix.decision == Decision.ALLOW

    def test_approve_changes_status_to_approved(self) -> None:
        matrix = PermissionMatrixAggregate.create(
            role_id="r",
            operation="op",
            resource_scope="s",
            data_scope="d",
            decision=Decision.ALLOW,
            tenant_id=uuid4(),
        )
        approved = matrix.approve("approver-001")
        assert approved.approval_status == ApprovalStatus.APPROVED
        assert approved.approved_by == "approver-001"
        # 原实例不变
        assert matrix.approval_status == ApprovalStatus.PENDING

    def test_reject_changes_status_to_rejected(self) -> None:
        matrix = PermissionMatrixAggregate.create(
            role_id="r",
            operation="op",
            resource_scope="s",
            data_scope="d",
            decision=Decision.ALLOW,
            tenant_id=uuid4(),
        )
        rejected = matrix.reject("approver-001")
        assert rejected.approval_status == ApprovalStatus.REJECTED
        assert rejected.approved_by == "approver-001"

    def test_is_effective_true_only_when_approved(self) -> None:
        tenant_id = uuid4()
        pending = PermissionMatrixAggregate.create(
            role_id="r", operation="op", resource_scope="s", data_scope="d",
            decision=Decision.ALLOW, tenant_id=tenant_id,
        )
        assert pending.is_effective() is False

        approved = pending.approve("a")
        assert approved.is_effective() is True

        rejected = pending.reject("a")
        assert rejected.is_effective() is False


class MenuTreeAggregateTest:
    """MenuTreeAggregate 菜单可见性测试。"""

    def test_create_sets_visible_true_by_default(self) -> None:
        menu = MenuTreeAggregate.create(menu_name="工作台", tenant_id=uuid4())
        assert menu.visible is True
        assert menu.sort_order == 0
        assert menu.parent_id is None

    def test_create_respects_explicit_visible_false(self) -> None:
        menu = MenuTreeAggregate.create(menu_name="隐藏菜单", tenant_id=uuid4(), visible=False)
        assert menu.visible is False

    def test_hide_sets_visible_false(self) -> None:
        menu = MenuTreeAggregate.create(menu_name="m", tenant_id=uuid4())
        hidden = menu.hide()
        assert hidden.visible is False
        assert menu.visible is True

    def test_show_sets_visible_true(self) -> None:
        menu = MenuTreeAggregate.create(menu_name="m", tenant_id=uuid4(), visible=False)
        shown = menu.show()
        assert shown.visible is True
        assert menu.visible is False

    def test_hide_then_show_roundtrip(self) -> None:
        menu = MenuTreeAggregate.create(menu_name="m", tenant_id=uuid4())
        assert menu.hide().show().visible is True