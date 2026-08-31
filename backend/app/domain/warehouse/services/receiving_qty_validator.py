"""收货数量校验服务 - 超收拒绝 + 部分收货支持。"""

from __future__ import annotations

from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class ReceivingQtyValidator:
    """收货数量校验领域服务。

    输入订单量/已收量/本次量/over_receive_ratio，输出是否允许收货。
    超收拒绝 EITP_WMS_RECEIVING_OVER_RECEIVED（spec 5.3.1.3）。
    部分收货累计正确。
    """

    @staticmethod
    def validate(
        ordered_qty: float,
        received_qty: float,
        current_qty: float,
        over_receive_ratio: float = 0.0,
    ) -> None:
        """校验本次收货数量是否允许。

        Args:
            ordered_qty: 订单数量
            received_qty: 已收数量
            current_qty: 本次收货数量
            over_receive_ratio: 超收比例（0.0 = 不允许超收，0.1 = 允许超收 10%）
        """
        if current_qty < 0:
            raise WMSError(
                WMSErrorCode.RECEIVING_OVER_RECEIVED,
                "收货数量不能为负",
            )

        max_allowed = ordered_qty * (1 + over_receive_ratio)
        total_after = received_qty + current_qty

        if total_after > max_allowed + 1e-9:
            raise WMSError(
                WMSErrorCode.RECEIVING_OVER_RECEIVED,
                f"收货数量超出允许范围: 已收 {received_qty} + 本次 {current_qty} > 最大允许 {max_allowed}",
                details={
                    "ordered_qty": ordered_qty,
                    "received_qty": received_qty,
                    "current_qty": current_qty,
                    "over_receive_ratio": over_receive_ratio,
                    "max_allowed": max_allowed,
                },
            )

    @staticmethod
    def can_receive(
        ordered_qty: float,
        received_qty: float,
        current_qty: float,
        over_receive_ratio: float = 0.0,
    ) -> bool:
        """是否允许收货（不抛异常）。"""
        try:
            ReceivingQtyValidator.validate(ordered_qty, received_qty, current_qty, over_receive_ratio)
            return True
        except WMSError:
            return False