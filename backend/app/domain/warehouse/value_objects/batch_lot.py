"""Batch/Lot/Serial 值对象 - P0 预留可空，P1 启用后按配置必填。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BatchLot:
    """批次/批号/序列号值对象 - P0 预留可空，P1 启用后按配置必填。

    batch_number: 批次号（同一生产批次）
    lot_number: 批号（同一生产批号，可跨批次）
    serial_number: 序列号（唯一标识单个商品）
    expiry_date: 有效期至
    production_date: 生产日期
    """

    batch_number: str | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    expiry_date: date | None = None
    production_date: date | None = None

    def is_empty(self) -> bool:
        """是否全部为空（P0 默认状态）。"""
        return (
            self.batch_number is None
            and self.lot_number is None
            and self.serial_number is None
            and self.expiry_date is None
            and self.production_date is None
        )

    def is_expired(self, today: date | None = None) -> bool:
        """是否已过期。"""
        if self.expiry_date is None:
            return False
        from datetime import date as _date
        check_date = today or _date.today()
        return check_date > self.expiry_date

    def is_near_expiry(self, threshold_days: int = 30, today: date | None = None) -> bool:
        """是否临近过期（默认 30 天内）。"""
        if self.expiry_date is None:
            return False
        from datetime import date as _date, timedelta
        check_date = today or _date.today()
        return check_date <= self.expiry_date <= check_date + timedelta(days=threshold_days)

    def composite_key(self) -> str:
        """组合键 - 用于 InventoryPosition 唯一性校验。"""
        return f"{self.batch_number or ''}|{self.lot_number or ''}|{self.serial_number or ''}"