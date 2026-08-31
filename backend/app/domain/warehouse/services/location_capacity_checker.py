"""库位容量校验器 - 入库时校验库位容量。"""

from __future__ import annotations

from app.domain.warehouse.aggregates.location_config_aggregate import (
    CapacityCheckResult,
    LocationConfigAggregate,
)
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


class LocationCapacityChecker:
    """入库时校验库位容量，超限按配置告警或拒绝。"""

    def check(
        self,
        location: LocationConfigAggregate,
        current_qty: float,
        add_qty: float,
    ) -> CapacityCheckResult:
        result = location.check_capacity(current_qty, add_qty)
        if not result.allowed:
            raise INVError(
                INVErrorCode.LOCATION_CAPACITY_EXCEEDED,
                result.message,
            )
        return result