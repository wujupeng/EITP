"""库存策略配置值对象 - 阈值配置与动作配置。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InvThresholdConfig:
    """库存阈值配置。"""
    safety_stock: float = 0.0
    min_stock: float = 0.0
    max_stock: float = 0.0
    reorder_point: float = 0.0
    eoq: float = 0.0
    alert_threshold: float = 0.0
    aging_days: int = 0
    abc_a_threshold: float = 0.8
    abc_b_threshold: float = 0.95
    periodic_days: int = 0


@dataclass(frozen=True)
class InvActionConfig:
    """库存动作配置。"""
    action_type: str = "alert"
    notify_channels: tuple[str, ...] = field(default_factory=tuple)
    notify_recipients: tuple[str, ...] = field(default_factory=tuple)
    auto_create_order: bool = False
    fifo_enforce: bool = False
    expire_action: str = "warn"