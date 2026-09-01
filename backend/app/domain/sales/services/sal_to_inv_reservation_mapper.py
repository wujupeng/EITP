"""SAL SalToInvReservationMapper 领域服务 - 销售→INV 预留映射（红线五核心）。

库存预留复用 INV-001 InventoryReservationAggregate，不重新实现预留引擎。
"""

from __future__ import annotations

from uuid import UUID

from app.domain.sales.aggregates.sales_order_aggregate import SalesOrderAggregate
from app.domain.sales.entities.sales_order_line import SalesOrderLine


class SalToInvReservationMapper:
    """销售到 INV 预留映射服务。

    输入：(订单, SKU, 数量, 仓库, 幂等键, 关联标识)
    输出：INV Reservation API 调用参数
    核心逻辑：订单行标识映射 source_line_id + 预留数量传递
            + 幂等键派生（sal:order:{order_id}:reserve）。

    红线五：不直接修改 inv_inventory_reservation 表，仅构建 API 调用参数。
    """

    @staticmethod
    def build_reservation_params(
        tenant_id: UUID,
        order: SalesOrderAggregate,
        line: SalesOrderLine,
        correlation_id: UUID | None = None,
    ) -> dict:
        """构建 INV Reservation API 创建预留参数。"""
        return {
            "tenant_id": str(tenant_id),
            "sku_id": str(line.enterprise_sku_id),
            "warehouse_id": (
                str(order.shipping_warehouse_id) if order.shipping_warehouse_id else None
            ),
            "quantity": line.ordered_quantity,
            "source_document_id": str(order.order_id),
            "source_document_type": "sal_order",
            "source_line_id": str(line.line_id),
            "idempotency_key": f"sal:order:{order.order_id}:reserve:{line.line_id}",
            "correlation_id": str(correlation_id or order.correlation_id or order.order_id),
        }

    @staticmethod
    def build_reservation_params_batch(
        tenant_id: UUID,
        order: SalesOrderAggregate,
        correlation_id: UUID | None = None,
    ) -> list[dict]:
        """批量构建 INV Reservation API 创建预留参数。"""
        return [
            SalToInvReservationMapper.build_reservation_params(
                tenant_id=tenant_id,
                order=order,
                line=line,
                correlation_id=correlation_id,
            )
            for line in order.lines
        ]

    @staticmethod
    def build_release_params(
        tenant_id: UUID,
        reservation_id: UUID,
        order_id: UUID,
        correlation_id: UUID | None = None,
    ) -> dict:
        """构建 INV Reservation API 释放预留参数。"""
        return {
            "tenant_id": str(tenant_id),
            "reservation_id": str(reservation_id),
            "idempotency_key": f"sal:order:{order_id}:release:{reservation_id}",
            "correlation_id": str(correlation_id or order_id),
        }

    @staticmethod
    def build_consume_params(
        tenant_id: UUID,
        reservation_id: UUID,
        consumed_quantity: float,
        shipment_id: UUID,
        correlation_id: UUID | None = None,
    ) -> dict:
        """构建 INV Reservation API 消费预留参数（预留转出库）。"""
        return {
            "tenant_id": str(tenant_id),
            "reservation_id": str(reservation_id),
            "consumed_quantity": consumed_quantity,
            "idempotency_key": f"sal:shipment:{shipment_id}:consume:{reservation_id}",
            "correlation_id": str(correlation_id or shipment_id),
        }