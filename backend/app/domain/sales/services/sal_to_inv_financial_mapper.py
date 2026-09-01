"""SAL SalToInvFinancialMapper 领域服务 - 销售→INV 收入映射（红线二核心）。

销售结算通过 INV Financial/Revenue API 落地销售收入与成本结转事实。
"""

from __future__ import annotations

from uuid import UUID

from app.domain.sales.aggregates.sales_settlement_aggregate import SalesSettlementAggregate
from app.domain.sales.entities.settlement_reconcile_line import SettlementReconcileLine
from app.domain.sales.value_objects.settlement_vo import SalesRevenue


class SalToInvFinancialMapper:
    """销售到 INV 收入映射服务。

    输入：(结算单, 订单行, 数量, 单价, 成本, 幂等键, 关联标识)
    输出：INV Financial/Revenue API 调用参数
    核心逻辑：收入金额 = 单价 × 数量 + 成本结转 = 移动平均成本 × 数量
            + 幂等键派生（sal:settlement:{settlement_id}:revenue）
            + 封装 SalesRevenue 值对象。

    红线二：不直接修改收入账本、应收账款事实、销售成本事实，仅构建 API 调用参数。
    """

    @staticmethod
    def build_revenue_params(
        tenant_id: UUID,
        settlement: SalesSettlementAggregate,
        line: SettlementReconcileLine,
        moving_avg_cost: float,
        correlation_id: UUID | None = None,
    ) -> dict:
        """构建 INV Financial/Revenue API 调用参数。"""
        revenue = SalesRevenue.from_trade(
            unit_price=line.unit_price,
            quantity=line.shipped_quantity,
            moving_avg_cost=moving_avg_cost,
        )
        return {
            "tenant_id": str(tenant_id),
            "document_id": str(settlement.settlement_id),
            "document_type": "sal_settlement",
            "order_id": str(settlement.order_id),
            "sku_id": str(line.enterprise_sku_id),
            "quantity": line.shipped_quantity,
            "unit_price": line.unit_price,
            "moving_avg_cost": moving_avg_cost,
            "revenue_amount": revenue.revenue_amount,
            "cost_amount": revenue.cost_amount,
            "gross_profit": revenue.gross_profit,
            "idempotency_key": (
                f"sal:settlement:{settlement.settlement_id}:revenue:{line.enterprise_sku_id}"
            ),
            "correlation_id": str(
                correlation_id or settlement.correlation_id or settlement.settlement_id
            ),
        }

    @staticmethod
    def build_revenue_params_batch(
        tenant_id: UUID,
        settlement: SalesSettlementAggregate,
        moving_avg_costs: dict[UUID, float],
        correlation_id: UUID | None = None,
    ) -> list[dict]:
        """批量构建 INV Financial/Revenue API 调用参数。"""
        return [
            SalToInvFinancialMapper.build_revenue_params(
                tenant_id=tenant_id,
                settlement=settlement,
                line=line,
                moving_avg_cost=moving_avg_costs.get(line.enterprise_sku_id, 0.0),
                correlation_id=correlation_id,
            )
            for line in settlement.reconcile_lines
        ]