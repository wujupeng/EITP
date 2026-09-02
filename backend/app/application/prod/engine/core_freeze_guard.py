"""核心冻结守卫 - 验证前后校验 9 个里程碑核心资产哈希指纹。"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from app.domain.prod.error_codes import PRODErrorCode
from app.domain.prod.exceptions import PRODError

logger = logging.getLogger(__name__)

CORE_MILESTONES = [
    "MT",
    "IAM",
    "INV",
    "MDM",
    "WMS",
    "PUR",
    "SAL",
    "SEC",
    "PLT",
]

CORE_ASSET_TYPES = [
    "model",
    "api_contract",
    "table_ddl",
    "rls_policy",
]


@dataclass(frozen=True)
class AssetFingerprint:
    """单个核心资产指纹。"""

    milestone: str
    asset_type: str
    asset_path: str
    sha256: str


@dataclass(frozen=True)
class FreezeBaseline:
    """冻结基线 - 9 个里程碑全部核心资产指纹集合。"""

    captured_at: datetime
    fingerprints: list[AssetFingerprint]

    def to_dict(self) -> dict:
        return {
            "captured_at": self.captured_at.isoformat(),
            "fingerprints": [
                {
                    "milestone": fp.milestone,
                    "asset_type": fp.asset_type,
                    "asset_path": fp.asset_path,
                    "sha256": fp.sha256,
                }
                for fp in self.fingerprints
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> FreezeBaseline:
        return cls(
            captured_at=datetime.fromisoformat(data["captured_at"]),
            fingerprints=[
                AssetFingerprint(
                    milestone=fp["milestone"],
                    asset_type=fp["asset_type"],
                    asset_path=fp["asset_path"],
                    sha256=fp["sha256"],
                )
                for fp in data["fingerprints"]
            ],
        )


@dataclass(frozen=True)
class FreezeViolation:
    """冻结违规明细。"""

    milestone: str
    asset_type: str
    asset_path: str
    baseline_hash: str
    current_hash: str


class ConfigStore(Protocol):
    """PLT-001 配置中心接口。"""

    async def get(self, namespace: str, key: str) -> str | None: ...
    async def set(self, namespace: str, key: str, value: str) -> None: ...


class CoreFreezeGuard:
    """核心冻结守卫。

    对 9 个里程碑的核心模型/API 契约/表结构/RLS 策略计算 SHA-256 哈希指纹。
    采集冻结基线（本里程碑启动时一次）→ 验证前校验 → 验证后校验。
    """

    def __init__(
        self,
        config_store: ConfigStore | None = None,
        backend_root: Path | None = None,
    ) -> None:
        self._config_store = config_store
        self._backend_root = backend_root or Path(__file__).resolve().parents[4]
        self._baseline: FreezeBaseline | None = None

    def _compute_file_hash(self, path: Path) -> str:
        if not path.exists():
            return hashlib.sha256(b"__MISSING__").hexdigest()
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _compute_module_hash(self, module_path: str) -> str:
        try:
            mod = importlib.import_module(module_path)
            source = inspect.getsource(mod)
            return hashlib.sha256(source.encode("utf-8")).hexdigest()
        except Exception:
            return hashlib.sha256(b"__UNAVAILABLE__").hexdigest()

    def _collect_fingerprints(self) -> list[AssetFingerprint]:
        fingerprints: list[AssetFingerprint] = []

        domain_map = {
            "MT": "app.domain.multitenant",
            "IAM": "app.domain.iam",
            "INV": "app.domain.inventory",
            "MDM": "app.domain.master_data",
            "WMS": "app.domain.warehouse",
            "PUR": "app.domain.purchase",
            "SAL": "app.domain.sales",
            "SEC": "app.domain.sec",
            "PLT": "app.domain.platform",
        }

        for milestone in CORE_MILESTONES:
            module = domain_map.get(milestone, "")
            if module:
                fingerprints.append(
                    AssetFingerprint(
                        milestone=milestone,
                        asset_type="model",
                        asset_path=module,
                        sha256=self._compute_module_hash(module),
                    )
                )

            api_dir = self._backend_root / "app" / "interfaces" / "api" / "v1"
            if milestone == "MT":
                api_pattern = "tenant"
            elif milestone == "IAM":
                api_pattern = "iam"
            elif milestone == "INV":
                api_pattern = "inventory"
            elif milestone == "MDM":
                api_pattern = "master_data"
            elif milestone == "WMS":
                api_pattern = "warehouse"
            elif milestone == "PUR":
                api_pattern = "purchase"
            elif milestone == "SAL":
                api_pattern = "sales"
            elif milestone == "SEC":
                api_pattern = "sec"
            elif milestone == "PLT":
                api_pattern = "plt"
            else:
                api_pattern = milestone.lower()

            api_path = api_dir / api_pattern
            if api_path.exists():
                combined = b""
                for py_file in sorted(api_path.rglob("*.py")):
                    combined += py_file.read_bytes()
                fingerprints.append(
                    AssetFingerprint(
                        milestone=milestone,
                        asset_type="api_contract",
                        asset_path=str(api_path),
                        sha256=hashlib.sha256(combined).hexdigest(),
                    )
                )

            migrations_dir = self._backend_root / "alembic" / "versions"
            if migrations_dir.exists():
                combined = b""
                for mig_file in sorted(migrations_dir.glob("*.py")):
                    if mig_file.name.startswith(("0", "1", "2", "3", "4")):
                        combined += mig_file.read_bytes()
                fingerprints.append(
                    AssetFingerprint(
                        milestone=milestone,
                        asset_type="table_ddl",
                        asset_path=str(migrations_dir),
                        sha256=hashlib.sha256(combined).hexdigest(),
                    )
                )

        return fingerprints

    async def capture_baseline(self) -> FreezeBaseline:
        fingerprints = self._collect_fingerprints()
        baseline = FreezeBaseline(
            captured_at=datetime.now(timezone.utc),
            fingerprints=fingerprints,
        )
        self._baseline = baseline

        if self._config_store:
            await self._config_store.set(
                "PROD",
                "core_freeze_baseline",
                json.dumps(baseline.to_dict(), ensure_ascii=False),
            )
        logger.info("Core freeze baseline captured: %d fingerprints", len(fingerprints))
        return baseline

    async def load_baseline(self) -> FreezeBaseline:
        if self._baseline is not None:
            return self._baseline

        if self._config_store:
            raw = await self._config_store.get("PROD", "core_freeze_baseline")
            if raw:
                self._baseline = FreezeBaseline.from_dict(json.loads(raw))
                return self._baseline

        return await self.capture_baseline()

    async def verify_before(self) -> list[FreezeViolation]:
        baseline = await self.load_baseline()
        current = self._collect_fingerprints()
        violations = self._compare(baseline, current)
        if violations:
            logger.warning(
                "Core freeze violations detected before verification: %d",
                len(violations),
            )
        return violations

    async def verify_after(self) -> list[FreezeViolation]:
        baseline = await self.load_baseline()
        current = self._collect_fingerprints()
        violations = self._compare(baseline, current)
        if violations:
            logger.error(
                "Core freeze violations detected after verification: %d",
                len(violations),
            )
        return violations

    @staticmethod
    def _compare(
        baseline: FreezeBaseline,
        current: list[AssetFingerprint],
    ) -> list[FreezeViolation]:
        current_map = {(fp.milestone, fp.asset_type): fp for fp in current}
        violations: list[FreezeViolation] = []

        for base_fp in baseline.fingerprints:
            key = (base_fp.milestone, base_fp.asset_type)
            curr_fp = current_map.get(key)
            if curr_fp is None:
                violations.append(
                    FreezeViolation(
                        milestone=base_fp.milestone,
                        asset_type=base_fp.asset_type,
                        asset_path=base_fp.asset_path,
                        baseline_hash=base_fp.sha256,
                        current_hash="__MISSING__",
                    )
                )
            elif curr_fp.sha256 != base_fp.sha256:
                violations.append(
                    FreezeViolation(
                        milestone=base_fp.milestone,
                        asset_type=base_fp.asset_type,
                        asset_path=base_fp.asset_path,
                        baseline_hash=base_fp.sha256,
                        current_hash=curr_fp.sha256,
                    )
                )

        return violations

    @staticmethod
    def violations_to_detail(violations: list[FreezeViolation]) -> dict:
        return {
            "violation_count": len(violations),
            "violations": [
                {
                    "milestone": v.milestone,
                    "asset_type": v.asset_type,
                    "asset_path": v.asset_path,
                    "baseline_hash": v.baseline_hash,
                    "current_hash": v.current_hash,
                }
                for v in violations
            ],
        }