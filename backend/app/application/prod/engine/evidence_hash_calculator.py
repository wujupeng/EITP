"""证据哈希计算器 - SHA-256 哈希计算与篡改检测。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceTriplet:
    """证据三元组哈希集合。"""

    report_hash: str
    metrics_snapshot_hash: str
    log_hash: str

    @property
    def aggregate_hash(self) -> str:
        raw = f"{self.report_hash}|{self.metrics_snapshot_hash}|{self.log_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class EvidenceHashCalculator:
    """证据哈希计算器。

    计算各证据 content_hash（SHA-256）+ 证据聚合哈希 + 事后校验。
    """

    @staticmethod
    def compute_content_hash(content: bytes | str | dict) -> str:
        if isinstance(content, bytes):
            return hashlib.sha256(content).hexdigest()
        if isinstance(content, str):
            return hashlib.sha256(content.encode("utf-8")).hexdigest()
        if isinstance(content, dict):
            canonical = json.dumps(content, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        raise TypeError(f"不支持的内容类型: {type(content)}")

    @staticmethod
    def compute_aggregate_hash(
        report_hash: str,
        metrics_snapshot_hash: str,
        log_hash: str,
    ) -> str:
        raw = f"{report_hash}|{metrics_snapshot_hash}|{log_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def compute_triplet(
        cls,
        report_content: bytes | str | dict,
        metrics_content: bytes | str | dict,
        log_content: bytes | str | dict,
    ) -> EvidenceTriplet:
        return EvidenceTriplet(
            report_hash=cls.compute_content_hash(report_content),
            metrics_snapshot_hash=cls.compute_content_hash(metrics_content),
            log_hash=cls.compute_content_hash(log_content),
        )

    @classmethod
    def verify_integrity(
        cls,
        stored_hash: str,
        report_content: bytes | str | dict,
        metrics_content: bytes | str | dict,
        log_content: bytes | str | dict,
    ) -> bool:
        current = cls.compute_aggregate_hash(
            cls.compute_content_hash(report_content),
            cls.compute_content_hash(metrics_content),
            cls.compute_content_hash(log_content),
        )
        return current == stored_hash

    @staticmethod
    def verify_single(stored_hash: str, content: bytes | str | dict) -> bool:
        return EvidenceHashCalculator.compute_content_hash(content) == stored_hash