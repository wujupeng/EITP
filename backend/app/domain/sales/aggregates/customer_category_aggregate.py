"""SAL CustomerCategoryAggregate 聚合根 - 客户分类。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.sales.value_objects.category_status import CategoryStatus
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


@dataclass
class CustomerCategoryAggregate:
    """客户分类聚合根 - 用于价格体系匹配/信用策略路由/审批路由。

    状态机：ACTIVE↔DISABLED。
    """

    category_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    category_code: str = ""
    category_name: str = ""
    description: str = ""
    status: CategoryStatus = CategoryStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def disable(self) -> None:
        """ACTIVE→DISABLED：停用分类。"""
        if self.status != CategoryStatus.ACTIVE:
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, "分类非启用状态不可停用")
        self.status = CategoryStatus.DISABLED
        self.updated_at = datetime.now(timezone.utc)

    def enable(self) -> None:
        """DISABLED→ACTIVE：启用分类。"""
        if self.status != CategoryStatus.DISABLED:
            raise SALError(SALErrorCode.ORDER_INVALID_STATE_TRANSITION, "分类非停用状态不可启用")
        self.status = CategoryStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_active(self) -> bool:
        return self.status == CategoryStatus.ACTIVE