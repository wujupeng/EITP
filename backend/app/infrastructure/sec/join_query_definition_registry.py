"""JoinQueryDefinitionRegistry - 跨表 JOIN 查询定义注册表。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JoinQueryDefinition:
    join_id: str
    module: str
    aggregate_root: str
    left_table: str
    right_table: str
    join_condition: str
    tenant_column_left: str = "tenant_id"
    tenant_column_right: str = "tenant_id"
    description: str = ""


class JoinQueryDefinitionRegistry:
    """注册所有跨表 JOIN 查询定义。"""

    def __init__(self) -> None:
        self._definitions: dict[str, JoinQueryDefinition] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            JoinQueryDefinition("sal-order-customer", "sal", "SalesOrder", "sal_sales_order", "sal_customer", "sal_sales_order.customer_id = sal_customer.customer_id", description="销售订单 JOIN 客户"),
            JoinQueryDefinition("sal-order-inventory", "sal", "SalesOrder", "sal_sales_order_line", "inv_inventory_balance", "sal_sales_order_line.sku_id = inv_inventory_balance.sku_id", description="销售订单 JOIN 库存"),
            JoinQueryDefinition("sal-shipment-order", "sal", "ShipmentOrder", "sal_shipment_order", "sal_sales_order", "sal_shipment_order.sales_order_id = sal_sales_order.sales_order_id", description="发货 JOIN 销售订单"),
            JoinQueryDefinition("pur-order-supplier", "pur", "PurchaseOrder", "pur_purchase_order", "pur_supplier", "pur_purchase_order.supplier_id = pur_supplier.supplier_id", description="采购订单 JOIN 供应商"),
            JoinQueryDefinition("pur-order-inventory", "pur", "PurchaseOrder", "pur_purchase_order_line", "inv_inventory_balance", "pur_purchase_order_line.sku_id = inv_inventory_balance.sku_id", description="采购订单 JOIN 库存"),
            JoinQueryDefinition("pur-receiving-order", "pur", "ReceivingOrder", "pur_receiving_order", "pur_purchase_order", "pur_receiving_order.purchase_order_id = pur_purchase_order.purchase_order_id", description="到货 JOIN 采购订单"),
            JoinQueryDefinition("inv-balance-warehouse", "inv", "InventoryBalance", "inv_inventory_balance", "wms_inventory_position", "inv_inventory_balance.sku_id = wms_inventory_position.sku_id", description="库存 JOIN 仓库位置"),
            JoinQueryDefinition("inv-balance-sku", "inv", "InventoryBalance", "inv_inventory_balance", "mdm_enterprise_sku", "inv_inventory_balance.sku_id = mdm_enterprise_sku.sku_id", description="库存 JOIN SKU"),
            JoinQueryDefinition("wms-task-position", "wms", "PickingTask", "wms_picking_task", "wms_inventory_position", "wms_picking_task.position_id = wms_inventory_position.position_id", description="拣货任务 JOIN 仓位"),
            JoinQueryDefinition("wms-shipping-order", "wms", "ShippingOrder", "wms_shipping_order", "sal_sales_order", "wms_shipping_order.sales_order_id = sal_sales_order.sales_order_id", description="WMS发货 JOIN 销售订单"),
        ]
        for d in defaults:
            self._definitions[d.join_id] = d

    def register(self, definition: JoinQueryDefinition) -> None:
        self._definitions[definition.join_id] = definition

    def get_all(self) -> list[JoinQueryDefinition]:
        return list(self._definitions.values())

    def get_by_module(self, module: str) -> list[JoinQueryDefinition]:
        return [d for d in self._definitions.values() if d.module == module]

    def get_by_aggregate_root(self, aggregate_root: str) -> list[JoinQueryDefinition]:
        return [d for d in self._definitions.values() if d.aggregate_root == aggregate_root]