"""SAL SalReconcileService 领域服务 - 销售↔WMS↔INV 三边对账（红线七）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class ReconcileDiffItem:
    """对账差异项。"""

    order_id: UUID
    shipment_id: UUID | None
    sku_id: UUID
    sal_shipped_qty: float
    wms_shipped_qty: float
    inv_on_hand_qty: float
    diff: float


@dataclass(frozen=True)
class ReconcileResult:
    """对账结果。"""

    tenant_id: UUID
    order_id: UUID
    consistent: bool
    diff_items: list[ReconcileDiffItem] = field(default_factory=list)
    reconciled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SalReconcileService:
    """销售↔WMS↔INV 三边对账服务。

    输入：(tenant, order_id)
    输出：差异列表
    核心逻辑：对比销售发货记录、WMS 发货记录、INV 库存变化三边
            + 发现不一致告警
            + 以 WMS/INV 为准修复销售发货状态（WMS/INV 是事实源，红线七）。

    红线七：销售业务状态、WMS 发货状态、INV 库存状态三边必须一致。
    """

    def __init__(self, diff_threshold: float = 0.01) -> None:
        self._diff_threshold = diff_threshold

    def reconcile(
        self,
        tenant_id: UUID,
        order_id: UUID,
        sal_shipped: dict[UUID, float],
        wms_shipped: dict[UUID, float],
        inv_on_hand: dict[UUID, float],
        expected_inv_on_hand: dict[UUID, float] | None = None,
    ) -> ReconcileResult:
        """三边对账。

        Args:
            sal_shipped: 销售记录的已发数量 {sku_id: qty}
            wms_shipped: WMS 记录的已发数量 {sku_id: qty}
            inv_on_hand: INV 当前库存 {sku_id: qty}
            expected_inv_on_hand: INV 期望库存（用于校验库存变化一致性）

        Returns:
            ReconcileResult
        """
        all_skus = set(sal_shipped) | set(wms_shipped) | set(inv_on_hand)
        diff_items: list[ReconcileDiffItem] = []

        for sku_id in all_skus:
            sal_qty = sal_shipped.get(sku_id, 0.0)
            wms_qty = wms_shipped.get(sku_id, 0.0)
            inv_qty = inv_on_hand.get(sku_id, 0.0)

            # 销售 vs WMS 差异
            sal_wms_diff = round(sal_qty - wms_qty, 2)
            if abs(sal_wms_diff) > self._diff_threshold:
                diff_items.append(
                    ReconcileDiffItem(
                        order_id=order_id,
                        shipment_id=None,
                        sku_id=sku_id,
                        sal_shipped_qty=sal_qty,
                        wms_shipped_qty=wms_qty,
                        inv_on_hand_qty=inv_qty,
                        diff=sal_wms_diff,
                    )
                )

            # INV 库存变化一致性校验
            if expected_inv_on_hand is not None:
                expected_inv = expected_inv_on_hand.get(sku_id, 0.0)
                inv_diff = round(inv_qty - expected_inv, 2)
                if abs(inv_diff) > self._diff_threshold:
                    diff_items.append(
                        ReconcileDiffItem(
                            order_id=order_id,
                            shipment_id=None,
                            sku_id=sku_id,
                            sal_shipped_qty=sal_qty,
                            wms_shipped_qty=wms_qty,
                            inv_on_hand_qty=inv_qty,
                            diff=inv_diff,
                        )
                    )

        return ReconcileResult(
            tenant_id=tenant_id,
            order_id=order_id,
            consistent=len(diff_items) == 0,
            diff_items=diff_items,
        )

    @staticmethod
    def repair_sal_shipped(
        sal_shipped: dict[UUID, float],
        wms_shipped: dict[UUID, float],
    ) -> dict[UUID, float]:
        """以 WMS 为准修复销售发货状态（WMS 是事实源）。"""
        return {sku: wms_shipped.get(sku, qty) for sku, qty in sal_shipped.items()} | {
            sku: qty for sku, qty in wms_shipped.items() if sku not in sal_shipped
        }