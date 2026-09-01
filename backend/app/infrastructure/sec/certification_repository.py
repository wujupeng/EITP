"""CertificationRepository - 认证基线仓储（批次/项/报告/证书/配置）。"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CertificationBatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, batch: dict[str, Any]) -> UUID:
        stmt = text("""
            INSERT INTO sec_certification_batch
                (batch_id, matrix_version, trigger_source, status, tenant_id, total_items, passed_count, failed_count, unexecutable_count)
            VALUES
                (:batch_id, :matrix_version, :trigger_source, :status, :tenant_id, :total_items, :passed_count, :failed_count, :unexecutable_count)
        """)
        await self._session.execute(stmt, {
            "batch_id": str(batch["batch_id"]),
            "matrix_version": batch["matrix_version"],
            "trigger_source": batch.get("trigger_source", "manual"),
            "status": batch.get("status", "pending"),
            "tenant_id": str(batch["tenant_id"]),
            "total_items": batch.get("total_items", 0),
            "passed_count": batch.get("passed_count", 0),
            "failed_count": batch.get("failed_count", 0),
            "unexecutable_count": batch.get("unexecutable_count", 0),
        })
        await self._session.flush()
        return batch["batch_id"]

    async def get_by_id(self, batch_id: UUID) -> dict[str, Any] | None:
        stmt = text("SELECT * FROM sec_certification_batch WHERE batch_id = :batch_id")
        result = await self._session.execute(stmt, {"batch_id": str(batch_id)})
        row = result.mappings().first()
        return dict(row) if row else None

    async def update_status(self, batch_id: UUID, status: str, **kwargs: Any) -> None:
        sets = ["status = :status"]
        params: dict[str, Any] = {"batch_id": str(batch_id), "status": status}
        for k, v in kwargs.items():
            sets.append(f"{k} = :{k}")
            params[k] = v
        stmt = text(f"UPDATE sec_certification_batch SET {', '.join(sets)} WHERE batch_id = :batch_id")
        await self._session.execute(stmt, params)


class CertificationItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, item: dict[str, Any]) -> str:
        stmt = text("""
            INSERT INTO sec_certification_item
                (item_id, batch_id, layer, operation, aggregate_root, attack_vector, expected_behavior, actual_behavior, conclusion, evidence, duration_ms, failure_reason, tenant_id)
            VALUES
                (:item_id, :batch_id, :layer, :operation, :aggregate_root, :attack_vector, :expected_behavior, :actual_behavior, :conclusion, :evidence, :duration_ms, :failure_reason, :tenant_id)
        """)
        await self._session.execute(stmt, {
            "item_id": item["item_id"],
            "batch_id": str(item["batch_id"]),
            "layer": item["layer"],
            "operation": item["operation"],
            "aggregate_root": item["aggregate_root"],
            "attack_vector": json.dumps(item.get("attack_vector", {})),
            "expected_behavior": item.get("expected_behavior", ""),
            "actual_behavior": item.get("actual_behavior", ""),
            "conclusion": item.get("conclusion", "pending"),
            "evidence": json.dumps(item.get("evidence", {})),
            "duration_ms": item.get("duration_ms", 0),
            "failure_reason": item.get("failure_reason", ""),
            "tenant_id": str(item["tenant_id"]),
        })
        await self._session.flush()
        return item["item_id"]

    async def get_by_batch(self, batch_id: UUID) -> list[dict[str, Any]]:
        stmt = text("SELECT * FROM sec_certification_item WHERE batch_id = :batch_id ORDER BY layer, operation")
        result = await self._session.execute(stmt, {"batch_id": str(batch_id)})
        return [dict(r) for r in result.mappings()]

    async def get_by_batch_and_conclusion(self, batch_id: UUID, conclusion: str) -> list[dict[str, Any]]:
        stmt = text("SELECT * FROM sec_certification_item WHERE batch_id = :batch_id AND conclusion = :conclusion")
        result = await self._session.execute(stmt, {"batch_id": str(batch_id), "conclusion": conclusion})
        return [dict(r) for r in result.mappings()]


class CertificationReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: dict[str, Any]) -> str:
        stmt = text("""
            INSERT INTO sec_certification_report
                (report_id, batch_id, matrix_version, executor, total_items, passed_count, failed_count, unexecutable_count, pass_rate, failed_items, evidence_index, report_json, report_html, tenant_id)
            VALUES
                (:report_id, :batch_id, :matrix_version, :executor, :total_items, :passed_count, :failed_count, :unexecutable_count, :pass_rate, :failed_items, :evidence_index, :report_json, :report_html, :tenant_id)
        """)
        await self._session.execute(stmt, {
            "report_id": report["report_id"],
            "batch_id": str(report["batch_id"]),
            "matrix_version": report["matrix_version"],
            "executor": report.get("executor", ""),
            "total_items": report.get("total_items", 0),
            "passed_count": report.get("passed_count", 0),
            "failed_count": report.get("failed_count", 0),
            "unexecutable_count": report.get("unexecutable_count", 0),
            "pass_rate": report.get("pass_rate", 0.0),
            "failed_items": json.dumps(report.get("failed_items", [])),
            "evidence_index": json.dumps(report.get("evidence_index", {})),
            "report_json": json.dumps(report.get("report_json", {})),
            "report_html": report.get("report_html", ""),
            "tenant_id": str(report["tenant_id"]),
        })
        await self._session.flush()
        return report["report_id"]

    async def get_by_id(self, report_id: str) -> dict[str, Any] | None:
        stmt = text("SELECT * FROM sec_certification_report WHERE report_id = :report_id")
        result = await self._session.execute(stmt, {"report_id": report_id})
        row = result.mappings().first()
        return dict(row) if row else None


class CertificationCertificateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, cert: dict[str, Any]) -> UUID:
        stmt = text("""
            INSERT INTO sec_certification_certificate
                (certificate_id, cert_number, matrix_version, cert_scope, issued_at, valid_until, issuer, signer, evidence_hash, signature, status, tenant_id)
            VALUES
                (:certificate_id, :cert_number, :matrix_version, :cert_scope, :issued_at, :valid_until, :issuer, :signer, :evidence_hash, :signature, :status, :tenant_id)
        """)
        await self._session.execute(stmt, {
            "certificate_id": str(cert["certificate_id"]),
            "cert_number": cert["cert_number"],
            "matrix_version": cert["matrix_version"],
            "cert_scope": json.dumps(cert.get("cert_scope", {})),
            "issued_at": cert.get("issued_at"),
            "valid_until": cert.get("valid_until"),
            "issuer": cert.get("issuer", ""),
            "signer": cert.get("signer", ""),
            "evidence_hash": cert.get("evidence_hash", ""),
            "signature": cert.get("signature", ""),
            "status": cert.get("status", "draft"),
            "tenant_id": str(cert["tenant_id"]),
        })
        await self._session.flush()
        return cert["certificate_id"]

    async def get_by_id(self, certificate_id: UUID) -> dict[str, Any] | None:
        stmt = text("SELECT * FROM sec_certification_certificate WHERE certificate_id = :certificate_id")
        result = await self._session.execute(stmt, {"certificate_id": str(certificate_id)})
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_by_number(self, cert_number: str) -> dict[str, Any] | None:
        stmt = text("SELECT * FROM sec_certification_certificate WHERE cert_number = :cert_number")
        result = await self._session.execute(stmt, {"cert_number": cert_number})
        row = result.mappings().first()
        return dict(row) if row else None


class CertificationConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, config: dict[str, Any]) -> UUID:
        stmt = text("""
            INSERT INTO sec_certification_config
                (config_id, matrix_layers, strict_mode, alert_channels, report_retention_days, item_skip_reasons, tenant_id)
            VALUES
                (:config_id, :matrix_layers, :strict_mode, :alert_channels, :report_retention_days, :item_skip_reasons, :tenant_id)
        """)
        await self._session.execute(stmt, {
            "config_id": str(config["config_id"]),
            "matrix_layers": json.dumps(config.get("matrix_layers", [])),
            "strict_mode": config.get("strict_mode", True),
            "alert_channels": json.dumps(config.get("alert_channels", [])),
            "report_retention_days": config.get("report_retention_days", 365),
            "item_skip_reasons": json.dumps(config.get("item_skip_reasons", {})),
            "tenant_id": str(config["tenant_id"]),
        })
        await self._session.flush()
        return config["config_id"]

    async def get_by_tenant(self, tenant_id: UUID) -> dict[str, Any] | None:
        stmt = text("SELECT * FROM sec_certification_config WHERE tenant_id = :tenant_id LIMIT 1")
        result = await self._session.execute(stmt, {"tenant_id": str(tenant_id)})
        row = result.mappings().first()
        return dict(row) if row else None