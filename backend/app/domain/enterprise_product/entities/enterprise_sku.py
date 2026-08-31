"""企业 SKU 实体 - 引用集团 SKU，继承集团 SKU 编码/规格/条码/计量单位。

企业级含 tenant_id（租户级隔离）。enterprise_sku_code 为空时继承集团 SKU 编码。
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from app.domain.shared.entity import EntityId


class EnterpriseSkuStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class EnterpriseSku:
    """企业 SKU 实体 - 引用集团 SKU，可补充企业特有条码。"""

    def __init__(
        self,
        enterprise_sku_id: EntityId,
        tenant_id: UUID,
        enterprise_product_id: EntityId,
        group_sku_id: UUID,
        enterprise_sku_code: str | None = None,
        enterprise_sku_name: str | None = None,
        enterprise_barcode_list: list[str] | None = None,
        status: EnterpriseSkuStatus = EnterpriseSkuStatus.ACTIVE,
    ) -> None:
        self._enterprise_sku_id = enterprise_sku_id
        self._tenant_id = tenant_id
        self._enterprise_product_id = enterprise_product_id
        self._group_sku_id = group_sku_id
        self._enterprise_sku_code = enterprise_sku_code
        self._enterprise_sku_name = enterprise_sku_name
        self._enterprise_barcode_list = enterprise_barcode_list or []
        self._status = status

    @property
    def enterprise_sku_id(self) -> EntityId:
        return self._enterprise_sku_id

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def enterprise_product_id(self) -> EntityId:
        return self._enterprise_product_id

    @property
    def group_sku_id(self) -> UUID:
        return self._group_sku_id

    @property
    def enterprise_sku_code(self) -> str | None:
        return self._enterprise_sku_code

    @property
    def enterprise_sku_name(self) -> str | None:
        return self._enterprise_sku_name

    @property
    def enterprise_barcode_list(self) -> list[str]:
        return self._enterprise_barcode_list

    @property
    def status(self) -> EnterpriseSkuStatus:
        return self._status

    def is_active(self) -> bool:
        return self._status == EnterpriseSkuStatus.ACTIVE

    def disable(self) -> None:
        self._status = EnterpriseSkuStatus.DISABLED

    def enable(self) -> None:
        self._status = EnterpriseSkuStatus.ACTIVE

    def resolve_sku_code(self, group_sku_code: str) -> str:
        """解析有效 SKU 编码：企业级为空时继承集团 SKU 编码。"""
        return self._enterprise_sku_code or group_sku_code

    def resolve_sku_name(self, group_sku_name: str) -> str:
        """解析有效 SKU 名称：企业级为空时继承集团 SKU 名称。"""
        return self._enterprise_sku_name or group_sku_name

    def add_barcode(self, barcode: str) -> None:
        if barcode not in self._enterprise_barcode_list:
            self._enterprise_barcode_list.append(barcode)