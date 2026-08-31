"""跨租户引用校验器 - 校验商品引用的分类/品牌/单位属于当前租户。"""

from __future__ import annotations

from uuid import UUID

from app.interfaces.middleware.error_handler import INVError, INVErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class CrossTenantRefChecker:
    """校验商品创建/修改时引用的 category_id/brand_id/base_unit_id 属于当前租户。"""

    def __init__(self) -> None:
        pass

    def check_tenant(self, ref_tenant_id: UUID, ref_type: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise INVError(INVErrorCode.CROSS_TENANT_REF_DENIED, "安全上下文缺失")
        current_tenant_id = ctx.tenant.tenant_id
        if isinstance(current_tenant_id, str):
            current_tenant_id = UUID(current_tenant_id)
        if ref_tenant_id != current_tenant_id:
            raise INVError(
                INVErrorCode.CROSS_TENANT_REF_DENIED,
                f"{ref_type} 租户 {ref_tenant_id} 与当前租户 {current_tenant_id} 不一致",
            )

    def check_category(self, category_tenant_id: UUID) -> None:
        self.check_tenant(category_tenant_id, "分类")

    def check_brand(self, brand_tenant_id: UUID) -> None:
        self.check_tenant(brand_tenant_id, "品牌")

    def check_unit(self, unit_tenant_id: UUID) -> None:
        self.check_tenant(unit_tenant_id, "计量单位")