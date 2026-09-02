"""PROD 集成测试 - 证据哈希链 + 篡改检测。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest
from app.application.prod.engine.evidence_hash_calculator import EvidenceHashCalculator


class TestProdEvidenceHashChain:
    """证据哈希链 + 篡改检测。"""

    def test_aggregate_hash_consistent(self):
        h1 = EvidenceHashCalculator.compute_aggregate_hash("a", "b", "c")
        h2 = EvidenceHashCalculator.compute_aggregate_hash("a", "b", "c")
        assert h1 == h2

    def test_tampered_report_detected(self):
        stored = EvidenceHashCalculator.compute_aggregate_hash("report", "metrics", "log")
        ok = EvidenceHashCalculator.verify_integrity(stored, "TAMPERED", "metrics", "log")
        assert not ok

    def test_tampered_metrics_detected(self):
        stored = EvidenceHashCalculator.compute_aggregate_hash("report", "metrics", "log")
        ok = EvidenceHashCalculator.verify_integrity(stored, "report", "TAMPERED", "log")
        assert not ok

    def test_no_tamper_passes(self):
        report_content = "report_data"
        metrics_content = "metrics_data"
        log_content = "log_data"
        triplet = EvidenceHashCalculator.compute_triplet(report_content, metrics_content, log_content)
        stored = triplet.aggregate_hash
        ok = EvidenceHashCalculator.verify_integrity(stored, report_content, metrics_content, log_content)
        assert ok