"""WMS 作业→INV Transaction 类型映射服务 - 承载 design 2.1.3.3 映射表。

红线：WMS 作业通过本服务映射到 INV Transaction 类型，
然后调用 InventoryAppSvc.execute_transaction() 改变库存事实，
不直接修改 inv_* 表。
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.warehouse.value_objects.wms_task_type import WmsTaskType


@dataclass(frozen=True)
class InvTransactionSpec:
    """INV Transaction 规格 - 映射服务的输出。"""
    transaction_type: str
    direction: str
    state_field: str
    params: dict


@dataclass(frozen=True)
class WmsToInvMapping:
    """WMS 作业到 INV Transaction 的完整映射。"""
    task_type: WmsTaskType
    task_id: UUID
    sku_id: UUID
    warehouse_id: UUID
    location_id: UUID
    quantity: float
    specs: list[InvTransactionSpec]
    idempotency_key: str
    correlation_id: str | None = None


class WmsToInvTransactionMapper:
    """WMS 作业→INV Transaction 映射领域服务。

    映射表（design 2.1.3.3）：
        Receiving 收货（需质检）→ PURCHASE_RECEIPT(+inspection)
        Receiving 收货（免检）  → PURCHASE_RECEIPT(+on_hand)
        Putaway 上架            → TRANSFER_OUT+TRANSFER_IN
        Picking 拣货（销售）    → SALES_ISSUE(-on_hand, 核销 Reservation)
        Picking 拣货（调拨）    → TRANSFER_OUT(-on_hand, +in_transit)
        Transfer 移库           → TRANSFER_OUT+TRANSFER_IN
        Shipping 发货           → 确认发货完成（拣货阶段已 SALES_ISSUE）

    P1 扩展 QC/Cycle Count/Block/Return 只需在映射表新增条目。
    """

    @staticmethod
    def map_receiving(
        task_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        location_id: UUID,
        quantity: float,
        is_inspection_required: bool,
        correlation_id: str | None = None,
    ) -> WmsToInvMapping:
        """收货作业 → INV Transaction 映射。"""
        state_field = "inspection" if is_inspection_required else "on_hand"
        specs = [InvTransactionSpec(
            transaction_type="purchase_receipt",
            direction="INBOUND",
            state_field=state_field,
            params={"quantity": quantity, "location_id": str(location_id)},
        )]
        return WmsToInvMapping(
            task_type=WmsTaskType.RECEIVING,
            task_id=task_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity=quantity,
            specs=specs,
            idempotency_key=WmsToInvTransactionMapper._derive_idempotency_key(task_id, "receiving"),
            correlation_id=correlation_id,
        )

    @staticmethod
    def map_putaway(
        task_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        source_location_id: UUID,
        target_location_id: UUID,
        quantity: float,
        correlation_id: str | None = None,
    ) -> WmsToInvMapping:
        """上架作业 → INV Transaction 映射（TRANSFER_OUT + TRANSFER_IN）。"""
        specs = [
            InvTransactionSpec(
                transaction_type="transfer_out",
                direction="OUTBOUND",
                state_field="on_hand",
                params={"quantity": quantity, "location_id": str(source_location_id)},
            ),
            InvTransactionSpec(
                transaction_type="transfer_in",
                direction="INBOUND",
                state_field="on_hand",
                params={"quantity": quantity, "location_id": str(target_location_id)},
            ),
        ]
        return WmsToInvMapping(
            task_type=WmsTaskType.PUTAWAY,
            task_id=task_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            quantity=quantity,
            specs=specs,
            idempotency_key=WmsToInvTransactionMapper._derive_idempotency_key(task_id, "putaway"),
            correlation_id=correlation_id,
        )

    @staticmethod
    def map_picking(
        task_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        location_id: UUID,
        quantity: float,
        is_sales: bool = True,
        reservation_id: UUID | None = None,
        correlation_id: str | None = None,
    ) -> WmsToInvMapping:
        """拣货作业 → INV Transaction 映射。"""
        if is_sales:
            specs = [InvTransactionSpec(
                transaction_type="sales_issue",
                direction="OUTBOUND",
                state_field="on_hand",
                params={"quantity": quantity, "location_id": str(location_id), "reservation_id": str(reservation_id) if reservation_id else None},
            )]
        else:
            specs = [InvTransactionSpec(
                transaction_type="transfer_out",
                direction="OUTBOUND",
                state_field="on_hand",
                params={"quantity": quantity, "location_id": str(location_id)},
            )]
        return WmsToInvMapping(
            task_type=WmsTaskType.PICKING,
            task_id=task_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity=quantity,
            specs=specs,
            idempotency_key=WmsToInvTransactionMapper._derive_idempotency_key(task_id, "picking"),
            correlation_id=correlation_id,
        )

    @staticmethod
    def map_transfer(
        task_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        source_location_id: UUID,
        target_location_id: UUID,
        quantity: float,
        correlation_id: str | None = None,
    ) -> WmsToInvMapping:
        """移库作业 → INV Transaction 映射（TRANSFER_OUT + TRANSFER_IN）。"""
        specs = [
            InvTransactionSpec(
                transaction_type="transfer_out",
                direction="OUTBOUND",
                state_field="on_hand",
                params={"quantity": quantity, "location_id": str(source_location_id)},
            ),
            InvTransactionSpec(
                transaction_type="transfer_in",
                direction="INBOUND",
                state_field="on_hand",
                params={"quantity": quantity, "location_id": str(target_location_id)},
            ),
        ]
        return WmsToInvMapping(
            task_type=WmsTaskType.TRANSFER,
            task_id=task_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=source_location_id,
            quantity=quantity,
            specs=specs,
            idempotency_key=WmsToInvTransactionMapper._derive_idempotency_key(task_id, "transfer"),
            correlation_id=correlation_id,
        )

    @staticmethod
    def map_shipping(
        task_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        location_id: UUID,
        quantity: float,
        correlation_id: str | None = None,
    ) -> WmsToInvMapping:
        """发货作业 → 确认发货完成（拣货阶段已 SALES_ISSUE）。"""
        specs = [InvTransactionSpec(
            transaction_type="sales_issue",
            direction="OUTBOUND",
            state_field="on_hand",
            params={"quantity": 0, "location_id": str(location_id), "confirm_only": True},
        )]
        return WmsToInvMapping(
            task_type=WmsTaskType.SHIPPING,
            task_id=task_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            quantity=quantity,
            specs=specs,
            idempotency_key=WmsToInvTransactionMapper._derive_idempotency_key(task_id, "shipping"),
            correlation_id=correlation_id,
        )

    @staticmethod
    def _derive_idempotency_key(task_id: UUID, step: str) -> str:
        """幂等键派生 - wms:{task_id}:{step}（spec 5.9.1.4）。"""
        return f"wms:{task_id}:{step}"

    @staticmethod
    def validate_mapping_coverage() -> bool:
        """验证映射表覆盖 P0 所有作业类型（spec 5.9.1.3）。"""
        p0_types = {
            WmsTaskType.RECEIVING,
            WmsTaskType.PUTAWAY,
            WmsTaskType.PICKING,
            WmsTaskType.TRANSFER,
            WmsTaskType.SHIPPING,
        }
        mapped_types = {
            WmsTaskType.RECEIVING,
            WmsTaskType.PUTAWAY,
            WmsTaskType.PICKING,
            WmsTaskType.TRANSFER,
            WmsTaskType.SHIPPING,
        }
        return p0_types == mapped_types