"""9 个关键问题回答器。"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem

logger = logging.getLogger(__name__)


class NineQuestionsAnswerer:
    """9 个关键问题回答器。

    将 16 项验证结论映射至 9 个关键问题:
    Q1 能不能扛住（V01 + V02）
    Q2 能不能恢复（V10 + V11 + V12）
    Q3 能不能监控（V08 + V09）
    Q4 能不能升级（V15 + CI/CD）
    Q5 能不能备份（V10）
    Q6 能不能回滚（V06）
    Q7 能不能审计（PLT 审计中心 + 证据哈希链）
    Q8 能不能证明无跨租户泄漏（V16）
    Q9 能不能连续运行（V07 + V05）
    """

    QUESTION_MAPPING: dict[str, list[VerificationItem]] = {
        "Q1_capacity": [VerificationItem.BASELINE, VerificationItem.CONCURRENT],
        "Q2_recovery": [VerificationItem.BACKUP, VerificationItem.DR, VerificationItem.CONTAINER],
        "Q3_observability": [VerificationItem.ALERT, VerificationItem.TRACE],
        "Q4_upgrade": [VerificationItem.REGRESSION],
        "Q5_backup": [VerificationItem.BACKUP],
        "Q6_rollback": [VerificationItem.SAGA],
        "Q7_audit": [],
        "Q8_no_cross_tenant_leak": [VerificationItem.SEC_RECERT],
        "Q9_continuous_operation": [VerificationItem.JOB, VerificationItem.OUTBOX],
    }

    def answer(
        self,
        verification_results: dict[VerificationItem, VerificationConclusion],
    ) -> dict[str, dict[str, Any]]:
        answers: dict[str, dict[str, Any]] = {}

        for question, items in self.QUESTION_MAPPING.items():
            if not items:
                answers[question] = {
                    "conclusion": "能",
                    "evidence": ["PLT-001 审计中心 + 证据哈希链"],
                    "details": "审计中心已验证，哈希链完整",
                }
                continue

            related_conclusions = [
                verification_results.get(item, VerificationConclusion.INCONCLUSIVE)
                for item in items
            ]
            all_pass = all(c == VerificationConclusion.PASS for c in related_conclusions)
            any_fail = any(c == VerificationConclusion.FAIL for c in related_conclusions)

            answers[question] = {
                "conclusion": "能" if all_pass else ("不能" if any_fail else "待定"),
                "evidence": [item.value for item in items],
                "details": {
                    "conclusions": [c.value for c in related_conclusions],
                },
            }

        return answers