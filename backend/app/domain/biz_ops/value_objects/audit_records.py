"""审计记录值对象 - 规则触发/策略触发/税务/信用/定价记录。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class RuleTriggerRecord:
    """规则触发记录。"""
    rule_key: str
    rule_type: str
    trigger_point: str
    result: str
    message: str = ""


@dataclass(frozen=True)
class StrategyTriggerRecord:
    """策略触发记录。"""
    strategy_id: UUID
    strategy_type: str
    target_ref: str
    result: str
    message: str = ""
    suggestion: str = ""


@dataclass(frozen=True)
class TaxCalcResultRecord:
    """税务计算结果记录。"""
    config_key: str
    total_tax: float
    total_amount: float


@dataclass(frozen=True)
class CreditCheckResult:
    """信用检查结果。"""
    customer_id: UUID
    used_amount: float
    credit_limit: float
    passed: bool
    message: str = ""


@dataclass(frozen=True)
class PricingApplyRecord:
    """定价应用记录。"""
    strategy_id: UUID
    strategy_type: str
    base_price: float
    final_price: float