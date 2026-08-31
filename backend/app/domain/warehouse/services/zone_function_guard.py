"""区功能匹配校验服务 - 校验作业类型与库区功能是否匹配。"""

from __future__ import annotations

from enum import Enum

from app.domain.warehouse.value_objects.zone_function import ZoneFunction
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class OperationType(str, Enum):
    """WMS 作业类型。"""
    RECEIVING = "receiving"
    QC = "qc"
    PUTAWAY = "putaway"
    PICKING = "picking"
    TRANSFER = "transfer"
    SHIPPING = "shipping"


_OPERATION_ALLOWED_ZONES: dict[OperationType, frozenset[ZoneFunction]] = {
    OperationType.RECEIVING: frozenset({ZoneFunction.RECEIVING, ZoneFunction.QC}),
    OperationType.QC: frozenset({ZoneFunction.QC}),
    OperationType.PUTAWAY: frozenset({ZoneFunction.STORAGE}),
    OperationType.PICKING: frozenset({ZoneFunction.PICKING, ZoneFunction.STORAGE}),
    OperationType.TRANSFER: frozenset({
        ZoneFunction.STORAGE,
        ZoneFunction.PICKING,
        ZoneFunction.RECEIVING,
        ZoneFunction.SHIPPING,
    }),
    OperationType.SHIPPING: frozenset({ZoneFunction.SHIPPING}),
}


class ZoneFunctionGuard:
    """区功能匹配校验服务 - 输入 zone_function 与作业类型，输出是否匹配。

    如收货作业需 zone_function ∈ {RECEIVING, QC}，
    上架作业需 zone_function = STORAGE，
    发货作业需 zone_function = SHIPPING。
    不匹配拒绝 EITP_WMS_ZONE_FUNCTION_MISMATCH。
    """

    @staticmethod
    def is_match(zone_function: ZoneFunction, operation: OperationType) -> bool:
        """校验库区功能与作业类型是否匹配。"""
        allowed = _OPERATION_ALLOWED_ZONES.get(operation, frozenset())
        return zone_function in allowed

    @staticmethod
    def validate(zone_function: ZoneFunction, operation: OperationType) -> None:
        """校验库区功能与作业类型匹配，不匹配则抛出异常。"""
        if not ZoneFunctionGuard.is_match(zone_function, operation):
            raise WMSError(
                WMSErrorCode.ZONE_FUNCTION_MISMATCH,
                f"库区功能 {zone_function.value} 不支持作业 {operation.value}",
                details={
                    "zone_function": zone_function.value,
                    "operation": operation.value,
                    "allowed": [zf.value for zf in _OPERATION_ALLOWED_ZONES.get(operation, frozenset())],
                },
            )

    @staticmethod
    def allowed_operations(zone_function: ZoneFunction) -> list[OperationType]:
        """返回该库区功能支持的所有作业类型。"""
        return [
            op for op in OperationType
            if zone_function in _OPERATION_ALLOWED_ZONES.get(op, frozenset())
        ]