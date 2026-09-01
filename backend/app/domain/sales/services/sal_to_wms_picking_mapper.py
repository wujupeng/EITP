"""SAL SalToWmsPickingMapper 领域服务 - 销售→WMS 拣货映射（红线一核心）。

销售发货通过 WMS Picking API 触发拣货作业，不直接修改库存。
"""

from __future__ import annotations

from uuid import UUID

from app.domain.sales.aggregates.shipment_order_aggregate import ShipmentOrderAggregate
from app.domain.sales.entities.shipment_line import ShipmentLine


class SalToWmsPickingMapper:
    """销售到 WMS 拣货映射服务。

    输入：(发货单, SKU, 数量, 仓库, 拣货策略, 幂等键, 关联标识)
    输出：WMS Picking API 调用参数
    核心逻辑：发货单标识映射 source_document_id + 拣货策略传递
            + 幂等键派生（sal:shipment:{shipment_id}:pick）+ CorrelationId 贯穿。

    红线一：不直接修改 inv_*/wms_inventory_position 表，仅构建 API 调用参数。
    """

    @staticmethod
    def build_picking_params(
        tenant_id: UUID,
        shipment: ShipmentOrderAggregate,
        line: ShipmentLine,
        correlation_id: UUID | None = None,
    ) -> dict:
        """构建 WMS Picking API 调用参数。"""
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
            ],
            "picking_strategy": shipment.picking_strategy.value,
            "idempotency_key": f"sal:shipment:{shipment.shipment_id}:pick",
            "correlation_id": str(
                correlation_id or shipment.correlation_id or shipment.shipment_id
            ),
        }

    @staticmethod
    def build_picking_params_batch(
        tenant_id: UUID,
        shipment: ShipmentOrderAggregate,
        correlation_id: UUID | None = None,
    ) -> dict:
        """批量构建 WMS Picking API 调用参数（含所有发货行）。"""
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
            "picking_strategy": shipment.picking_strategy.value,
            "idempotency_key": f"sal:shipment:{shipment.shipment_id}:pick",
            "correlation_id": str(
                correlation_id or shipment.correlation_id or shipment.shipment_id
            ),
        }