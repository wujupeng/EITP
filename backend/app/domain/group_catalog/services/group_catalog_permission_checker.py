"""集团商品目录权限校验器 - 校验集团级操作仅由集团主数据管理员执行。

企业管理员修改集团商品目录被拒绝（spec 5.1.1.9）并记录越权审计。
"""

from __future__ import annotations

from uuid import UUID

from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class GroupCatalogPermissionChecker:
    """集团商品目录权限校验器。

    集团商品目录操作仅由集团主数据管理员（平台级角色 mdm:group_product:manage）执行。
    企业管理员（非平台管理员）修改集团商品目录被拒绝。
    """

    GROUP_MANAGE_PERMISSION = "mdm:group_product:manage"
    GROUP_APPROVE_PERMISSION = "mdm:group_product:approve"
    GROUP_SKU_PERMISSION = "mdm:group_sku:manage"
    GROUP_CATEGORY_PERMISSION = "mdm:group_category:manage"
    GROUP_BRAND_PERMISSION = "mdm:group_brand:manage"
    GROUP_UNIT_PERMISSION = "mdm:group_unit:manage"

    @classmethod
    def enforce_manage(cls) -> None:
        """校验当前用户有集团商品管理权限。"""
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(
                MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED,
                "未认证，缺少安全上下文",
            )
        if not ctx.is_authorized(cls.GROUP_MANAGE_PERMISSION):
            raise MDMError(
                MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED,
                "仅集团主数据管理员可操作集团商品目录",
            )

    @classmethod
    def enforce_approve(cls) -> None:
        """校验当前用户有集团商品审批权限。"""
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(
                MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED,
                "未认证，缺少安全上下文",
            )
        if not ctx.is_authorized(cls.GROUP_APPROVE_PERMISSION):
            raise MDMError(
                MDMErrorCode.GROUP_CATALOG_PERMISSION_DENIED,
                "仅集团主数据审批员可审批集团商品",
            )

    @classmethod
    def enforce_category_manage(cls) -> None:
        """校验当前用户有集团分类管理权限。"""
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(
                MDMErrorCode.GROUP_CATEGORY_PERMISSION_DENIED,
                "未认证，缺少安全上下文",
            )
        if not ctx.is_authorized(cls.GROUP_CATEGORY_PERMISSION):
            raise MDMError(
                MDMErrorCode.GROUP_CATEGORY_PERMISSION_DENIED,
                "仅集团主数据管理员可管理集团分类",
            )

    @classmethod
    def enforce_unit_manage(cls) -> None:
        """校验当前用户有集团单位管理权限。"""
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(
                MDMErrorCode.GROUP_UNIT_PERMISSION_DENIED,
                "未认证，缺少安全上下文",
            )
        if not ctx.is_authorized(cls.GROUP_UNIT_PERMISSION):
            raise MDMError(
                MDMErrorCode.GROUP_UNIT_PERMISSION_DENIED,
                "仅集团主数据管理员可管理集团单位",
            )

    @classmethod
    def is_platform_admin(cls) -> bool:
        """检查当前用户是否为平台管理员。"""
        ctx = SecurityContext.current()
        if ctx is None:
            return False
        return ctx.user.is_platform_admin