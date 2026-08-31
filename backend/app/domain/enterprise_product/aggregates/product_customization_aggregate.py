"""商品定制聚合根 - 企业级差异化定制，租户级隔离（spec 5.2.1.7）。

企业定制仅可覆盖企业级属性（价格/库存策略/安全库存/成本模型/自定义属性），
不可修改集团基准属性（spec 5.2.1.10）。
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from uuid import UUID

from app.domain.enterprise_product.events.enterprise_product_events import (
    EnterpriseCustomizationPublishedEvent,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class InventoryStrategy(str, Enum):
    STRICT = "strict"
    ALLOW = "allow"
    WARNING = "warning"
    APPROVAL = "approval"


class CostModelType(str, Enum):
    MOVING_AVERAGE = "moving_average"
    WEIGHTED_AVERAGE = "weighted_average"
    FIFO = "fifo"
    STANDARD_COST = "standard_cost"
    ACTUAL_COST = "actual_cost"


class ProductCustomizationAggregate(AggregateRoot):
    """商品定制聚合根 - 企业级差异化定制。

    仅覆盖企业级属性，不可修改集团基准属性。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        enterprise_product_id: UUID,
        enterprise_sku_id: UUID | None = None,
        sales_price: Decimal | None = None,
        purchase_price: Decimal | None = None,
        inventory_strategy: InventoryStrategy | None = None,
        safety_stock: Decimal | None = None,
        cost_model: CostModelType | None = None,
        custom_attributes: dict | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._enterprise_product_id = enterprise_product_id
        self._enterprise_sku_id = enterprise_sku_id
        self._sales_price = sales_price
        self._purchase_price = purchase_price
        self._inventory_strategy = inventory_strategy
        self._safety_stock = safety_stock
        self._cost_model = cost_model
        self._custom_attributes = custom_attributes or {}
        self._version = version

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def enterprise_product_id(self) -> UUID:
        return self._enterprise_product_id

    @property
    def enterprise_sku_id(self) -> UUID | None:
        return self._enterprise_sku_id

    @property
    def sales_price(self) -> Decimal | None:
        return self._sales_price

    @property
    def purchase_price(self) -> Decimal | None:
        return self._purchase_price

    @property
    def inventory_strategy(self) -> InventoryStrategy | None:
        return self._inventory_strategy

    @property
    def safety_stock(self) -> Decimal | None:
        return self._safety_stock

    @property
    def cost_model(self) -> CostModelType | None:
        return self._cost_model

    @property
    def custom_attributes(self) -> dict:
        return self._custom_attributes

    @property
    def version(self) -> int:
        return self._version

    def update_sales_price(self, price: Decimal) -> None:
        if price < 0:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                "销售价格不能为负",
            )
        self._sales_price = price
        self._touch()

    def update_purchase_price(self, price: Decimal) -> None:
        if price < 0:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                "采购价格不能为负",
            )
        self._purchase_price = price
        self._touch()

    def update_inventory_strategy(self, strategy: InventoryStrategy) -> None:
        self._inventory_strategy = strategy
        self._touch()

    def update_safety_stock(self, stock: Decimal) -> None:
        if stock < 0:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                "安全库存不能为负",
            )
        self._safety_stock = stock
        self._touch()

    def update_cost_model(self, model: CostModelType) -> None:
        self._cost_model = model
        self._touch()

    def update_custom_attributes(self, attrs: dict) -> None:
        self._custom_attributes = attrs
        self._touch()

    def publish(self, new_version: int) -> None:
        if new_version <= self._version:
            raise MDMError(
                MDMErrorCode.SPEC_INSTANCE_INVALID,
                f"定制版本号 {new_version} 必须大于当前版本 {self._version}",
            )
        self._version = new_version
        self._touch()
        self._record_event(
            EnterpriseCustomizationPublishedEvent(
                tenant_id=self._tenant_id,
                customization_id=self._id.value,
                enterprise_product_id=self._enterprise_product_id,
                version=new_version,
            )
        )