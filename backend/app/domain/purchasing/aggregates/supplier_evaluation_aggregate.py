"""PUR SupplierGrade 枚举 + SupplierEvaluationAggregate 聚合根。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class SupplierGrade(str, Enum):
    QUALIFIED = "qualified"
    CONDITIONAL = "conditional"
    UNQUALIFIED = "unqualified"


@dataclass
class SupplierEvaluationAggregate:
    """供应商评估聚合根。"""

    evaluation_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    supplier_id: UUID = field(default_factory=uuid4)
    evaluation_period: str = ""
    on_time_delivery_rate: float = 0.0
    quality_pass_rate: float = 0.0
    response_speed_score: float | None = None
    overall_score: float = 0.0
    grade: SupplierGrade = SupplierGrade.UNQUALIFIED
    evaluated_by: UUID | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not 0 <= self.on_time_delivery_rate <= 1:
            raise PURError(PURErrorCode.SUPPLIER_SCOPE_MISMATCH, "准时交货率应在0-1之间")
        if not 0 <= self.quality_pass_rate <= 1:
            raise PURError(PURErrorCode.SUPPLIER_SCOPE_MISMATCH, "质量合格率应在0-1之间")
        if self.response_speed_score is not None and not 0 <= self.response_speed_score <= 100:
            raise PURError(PURErrorCode.SUPPLIER_SCOPE_MISMATCH, "响应速度评分应在0-100之间")

    def calculate_grade(self) -> SupplierGrade:
        delivery_score = self.on_time_delivery_rate * 40
        quality_score = self.quality_pass_rate * 40
        response_score = (self.response_speed_score or 0) * 0.2
        self.overall_score = round(delivery_score + quality_score + response_score, 2)
        if self.overall_score >= 90:
            self.grade = SupplierGrade.QUALIFIED
        elif self.overall_score >= 70:
            self.grade = SupplierGrade.CONDITIONAL
        else:
            self.grade = SupplierGrade.UNQUALIFIED
        return self.grade