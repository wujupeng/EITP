"""PROD EvidenceHashCalculator 单元测试 - SHA-256 哈希计算与篡改检测。

覆盖 compute_content_hash 对 bytes/str/dict 三种类型的 SHA-256 计算、
不支持类型抛 TypeError、compute_aggregate_hash 拼接格式、
EvidenceTriplet.aggregate_hash 属性一致性、
verify_integrity 与 verify_single 的正确/篡改判定。
"""

from __future__ import annotations

import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.application.prod.engine.evidence_hash_calculator import (
    EvidenceHashCalculator,
    EvidenceTriplet,
)


class EvidenceHashCalculatorTest:
    """EvidenceHashCalculator SHA-256 计算与完整性校验测试。"""

    def test_compute_content_hash_bytes_returns_sha256(self) -> None:
        content = b"prod-evidence-raw"
        expected = hashlib.sha256(content).hexdigest()
        result = EvidenceHashCalculator.compute_content_hash(content)
        assert result == expected
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_content_hash_str_returns_sha256(self) -> None:
        content = "生产验证证据文本"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert EvidenceHashCalculator.compute_content_hash(content) == expected

    def test_compute_content_hash_dict_uses_canonical_json(self) -> None:
        # dict 走 json.dumps(sort_keys=True) 规范化，键顺序不影响哈希
        import json

        d1 = {"b": 2, "a": 1}
        d2 = {"a": 1, "b": 2}
        canonical = json.dumps(d1, sort_keys=True, ensure_ascii=False)
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert EvidenceHashCalculator.compute_content_hash(d1) == expected
        # 不同键顺序应产生相同哈希
        assert EvidenceHashCalculator.compute_content_hash(d1) == EvidenceHashCalculator.compute_content_hash(d2)

    def test_compute_content_hash_unsupported_type_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            EvidenceHashCalculator.compute_content_hash(12345)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            EvidenceHashCalculator.compute_content_hash([1, 2, 3])  # type: ignore[arg-type]

    def test_compute_aggregate_hash_concatenates_with_separator(self) -> None:
        r, m, l = "h_r", "h_m", "h_l"
        expected = hashlib.sha256(f"{r}|{m}|{l}".encode("utf-8")).hexdigest()
        assert EvidenceHashCalculator.compute_aggregate_hash(r, m, l) == expected
        assert len(EvidenceHashCalculator.compute_aggregate_hash(r, m, l)) == 64

    def test_compute_triplet_aggregate_hash_property_consistent(self) -> None:
        triplet = EvidenceHashCalculator.compute_triplet(
            report_content=b"report",
            metrics_content={"qps": 1000},
            log_content="log-line",
        )
        assert isinstance(triplet, EvidenceTriplet)
        # aggregate_hash 属性应等价于 compute_aggregate_hash(三段)
        expected_agg = EvidenceHashCalculator.compute_aggregate_hash(
            triplet.report_hash, triplet.metrics_snapshot_hash, triplet.log_hash
        )
        assert triplet.aggregate_hash == expected_agg
        # 三段哈希均为 64 位十六进制
        for h in (triplet.report_hash, triplet.metrics_snapshot_hash, triplet.log_hash, triplet.aggregate_hash):
            assert len(h) == 64

    def test_verify_integrity_true_and_false(self) -> None:
        report, metrics, log = b"r", b"m", b"l"
        stored = EvidenceHashCalculator.compute_aggregate_hash(
            EvidenceHashCalculator.compute_content_hash(report),
            EvidenceHashCalculator.compute_content_hash(metrics),
            EvidenceHashCalculator.compute_content_hash(log),
        )
        # 内容一致 → True
        assert EvidenceHashCalculator.verify_integrity(stored, report, metrics, log) is True
        # 篡改 report 内容 → False
        assert EvidenceHashCalculator.verify_integrity(stored, b"r-tampered", metrics, log) is False
        # 篡改 stored_hash → False
        assert EvidenceHashCalculator.verify_integrity("0" * 64, report, metrics, log) is False

    def test_verify_single_true_and_false(self) -> None:
        content = "single-evidence"
        stored = EvidenceHashCalculator.compute_content_hash(content)
        assert EvidenceHashCalculator.verify_single(stored, content) is True
        assert EvidenceHashCalculator.verify_single(stored, "tampered") is False
        assert EvidenceHashCalculator.verify_single("0" * 64, content) is False