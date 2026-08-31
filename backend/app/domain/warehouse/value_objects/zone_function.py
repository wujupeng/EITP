"""区功能枚举 - 仓库内库区的六种功能分区。"""

from __future__ import annotations

from enum import Enum

from app.domain.inventory.value_objects.shared import LocationType


class ZoneFunction(str, Enum):
    """库区功能类型 - 对应仓储作业流程的六个环节。"""

    RECEIVING = "receiving"
    STORAGE = "storage"
    PICKING = "picking"
    SHIPPING = "shipping"
    QC = "qc"
    BLOCKED = "blocked"


_ZONE_FUNCTION_TO_LOCATION_TYPE: dict[ZoneFunction, LocationType] = {
    ZoneFunction.RECEIVING: LocationType.RECEIVING,
    ZoneFunction.STORAGE: LocationType.STORAGE,
    ZoneFunction.PICKING: LocationType.PICKING,
    ZoneFunction.SHIPPING: LocationType.STORAGE,
    ZoneFunction.QC: LocationType.INSPECTION,
    ZoneFunction.BLOCKED: LocationType.STORAGE,
}


def location_type_for_zone_function(zf: ZoneFunction) -> LocationType:
    """将 WMS ZoneFunction 映射到 INV LocationType，不修改 INV 枚举。"""
    return _ZONE_FUNCTION_TO_LOCATION_TYPE[zf]