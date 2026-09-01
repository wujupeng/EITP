"""SAL SalToWmsShippingMapper 领域服务 - 销售→WMS 发货映射（红线一核心）。

销售发货通过 WMS Shipping API 触发发货，WMS 内部调 INV SALES_SHIPMENT 落地 -on_hand。
"""

from __future__ import annotations

from uuid import UUID

from app.domain.sales.aggregates.shipment_order_aggregate import ShipmentOrderAggregate


class SalToWmsShippingMapper:
    """销售到 WMS 发货映射服务。

    输入：(发货单, SKU, 数量, 物流单号, 幂等键, 关联标识)
    输出：WMS Shipping API 调用参数
    核心逻辑：发货单标识映射 + 物流单号传递 + 幂等键派生（sal:shipment:{shipment_id}:ship）。

    红线一：不直接修改 inv_*/wms_inventory_position 表，仅构建 API 调用参数。
    """

    @staticmethod
    def build_shipping_params(
        tenant_id: UUID,
        shipment: ShipmentOrderAggregate,
        logistics_no: str,
        carrier: str | None = None,
        correlation_id: UUID | None = None,
    ) -> dict:
        """构建 WMS Shipping API 调用参数。"""
        return {
            "tenant_id": str(tenant_id),
            "source_document_id": str(shipment.shipment_id),
            "source_document_type": "sal_shipment",
            "warehouse_id": str(shipment.shipping_warehouse_id),
            "lines": [
                {
                    "sku_id": str(line.enterprise_sku_id),
                    "quantity": line.ship_quantity,
                    "order_line_id": str(line.order_line_id),
                }
                for line in shipment.lines
            ],
            "logistics_no": logistics_no,
            "carrier": carrier or shipment.carrier or "",
            "idempotency_key": f"sal:shipment:{shipment.shipment_id}:ship",
            "correlation_id": str(
                correlation_id or shipment.correlation_id or shipment.shipment_id
            ),
        }