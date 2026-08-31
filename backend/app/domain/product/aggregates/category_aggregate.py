"""分类聚合根 - 树形结构，禁止循环引用。"""

from __future__ import annotations

from uuid import UUID

from app.domain.inventory.value_objects.shared import ProductStatus
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


class CategoryAggregate(AggregateRoot):
    """商品分类聚合根 - 树形结构，自引用 parent_category_id。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        category_code: str,
        category_name: str,
        parent_category_id: UUID | None = None,
        level: int = 1,
        status: ProductStatus = ProductStatus.ACTIVE,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._category_code = category_code
        self._category_name = category_name
        self._parent_category_id = parent_category_id
        self._level = level
        self._status = status

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def category_code(self) -> str:
        return self._category_code

    @property
    def category_name(self) -> str:
        return self._category_name

    @property
    def parent_category_id(self) -> UUID | None:
        return self._parent_category_id

    @property
    def level(self) -> int:
        return self._level

    @property
    def status(self) -> ProductStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == ProductStatus.ACTIVE

    def validate_no_cycle(self, ancestor_ids: list[UUID]) -> None:
        if self._id.value in ancestor_ids:
            raise INVError(
                INVErrorCode.CATEGORY_DUPLICATE,
                f"分类 {self._category_code} 形成循环引用",
            )

    def is_root(self) -> bool:
        return self._parent_category_id is None