"""租户级审计日志 - 不可篡改，仅追加。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class AuditAction(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    LOGIN = "login"
    LOGOUT = "logout"
    CONFIG_CHANGE = "config_change"
    DATASCOPE_VIOLATION = "datascope_violation"
    GROUP_READONLY_VIOLATION = "group_readonly_violation"
    MASTER_PROPAGATE = "master_propagate"
    STOCK_CHANGE = "stock_change"
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_RELEASED = "reservation_released"
    STATE_TRANSITION = "state_transition"
    NEGATIVE_STOCK_FORCED = "negative_stock_forced"
    ADJUSTMENT_EXECUTED = "adjustment_executed"
    BLOCK_EXECUTED = "block_executed"
    UNBLOCK_EXECUTED = "unblock_executed"
    COUNT_DIFF_PROCESSED = "count_diff_processed"
    COST_MODEL_SWITCHED = "cost_model_switched"
    MASTER_DATA_PUBLISHED = "master_data_published"
    MASTER_DATA_VERSION_ROLLBACK = "master_data_version_rollback"
    GOVERNANCE_REQUEST_SUBMITTED = "governance_request_submitted"
    GOVERNANCE_REQUEST_APPROVED = "governance_request_approved"
    GOVERNANCE_REQUEST_REJECTED = "governance_request_rejected"
    GOVERNANCE_REQUEST_PUBLISHED = "governance_request_published"
    GOVERNANCE_REQUEST_ROLLBACK = "governance_request_rollback"
    ENTERPRISE_PRODUCT_REFERENCED = "enterprise_product_referenced"
    ENTERPRISE_REFERENCE_RELEASED = "enterprise_reference_released"
    NEGATIVE_POLICY_CHANGED = "negative_policy_changed"
    GROUP_CATALOG_PUBLISHED = "group_catalog_published"
    ENTERPRISE_CUSTOMIZATION_PUBLISHED = "enterprise_customization_published"
    WMS_SPACE_CHANGED = "wms_space_changed"
    WMS_TASK_CREATED = "wms_task_created"
    WMS_TASK_ASSIGNED = "wms_task_assigned"
    WMS_TASK_CLAIMED = "wms_task_claimed"
    WMS_TASK_COMPLETED = "wms_task_completed"
    WMS_TASK_CANCELLED = "wms_task_cancelled"
    WMS_TASK_FAILED = "wms_task_failed"
    WMS_RECEIVING_EXECUTED = "wms_receiving_executed"
    WMS_PUTAWAY_EXECUTED = "wms_putaway_executed"
    WMS_PICKING_EXECUTED = "wms_picking_executed"
    WMS_TRANSFER_EXECUTED = "wms_transfer_executed"
    WMS_SHIPPING_EXECUTED = "wms_shipping_executed"
    WMS_POSITION_SYNCED = "wms_position_synced"
    WMS_RECONCILE_DIFF_FOUND = "wms_reconcile_diff_found"

    CERT_EXECUTE = "cert_execute"
    ITEM_PASS = "item_pass"
    ITEM_FAIL = "item_fail"
    ITEM_UNEXECUTABLE = "item_unexecutable"
    CERT_ISSUE = "cert_issue"
    CERT_REVOKE = "cert_revoke"
    CERT_CONFIG_CHANGE = "cert_config_change"
    AUDIT_TAMPER_ATTEMPT = "audit_tamper_attempt"
    PLATFORM_ADMIN_ACCESS_REQUEST = "platform_admin_access_request"
    PLATFORM_ADMIN_BUSINESS_ACCESS = "platform_admin_business_access"
    PLATFORM_ADMIN_BUSINESS_WRITE_DENIED = "platform_admin_business_write_denied"
    REDIS_KEY_VIOLATION = "redis_key_violation"
    CROSS_TENANT_ACCESS_BLOCKED = "cross_tenant_access_blocked"
    CROSS_TENANT_REF_BLOCKED = "cross_tenant_ref_blocked"
    JOIN_CROSS_TENANT_LEAK = "join_cross_tenant_leak"
    E2E_ATTACK_CHAIN_EXECUTE = "e2e_attack_chain_execute"

    AUDIT_TAMPER_DETECTED = "audit_tamper_detected"
    AUDIT_QUERY = "audit_query"
    TAMPER_CHECK = "tamper_check"
    ARCHIVE = "archive"
    OUTBOX_DELIVERED = "outbox_delivered"
    OUTBOX_DEAD_LETTER = "outbox_dead_letter"
    SAGA_STARTED = "saga_started"
    SAGA_COMPENSATED = "saga_compensated"
    SAGA_MANUAL_INTERVENTION = "saga_manual_intervention"
    CONFIG_GRAY_RELEASE = "config_gray_release"
    TENANT_FROZEN = "tenant_frozen"
    TENANT_ARCHIVED = "tenant_archived"
    QUOTA_EXCEEDED = "quota_exceeded"
    JOB_TIMEOUT = "job_timeout"
    RATE_LIMITED = "rate_limited"
    CERT_GATE_BLOCKED = "cert_gate_blocked"

    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_COMPLETED = "verification_completed"
    VERIFICATION_FAILED = "verification_failed"
    EVIDENCE_COLLECTED = "evidence_collected"
    DOSSIER_ASSEMBLED = "dossier_assembled"
    DOSSIER_SIGNED = "dossier_signed"
    DOSSIER_TAMPER_DETECTED = "dossier_tamper_detected"
    BASELINE_DEGRADED = "baseline_degraded"
    DR_SWITCHOVER_EXECUTED = "dr_switchover_executed"
    SEC_RECERT_ISSUED = "sec_recert_issued"
    CORE_FREEZE_VIOLATED = "core_freeze_violated"
    FAULT_INJECTION_EXECUTED = "fault_injection_executed"
    BACKUP_EXECUTED = "backup_executed"
    RESTORE_EXECUTED = "restore_executed"

    SEAL_REQUESTED = "seal_requested"
    SEAL_GATE_PASSED = "seal_gate_passed"
    SEAL_GATE_FAILED = "seal_gate_failed"
    ASSET_SNAPSHOT_COLLECTED = "asset_snapshot_collected"
    ASSET_SNAPSHOT_TAMPERED = "asset_snapshot_tampered"
    GIT_TAG_CREATED = "git_tag_created"
    GIT_TAG_PUSHED = "git_tag_pushed"
    MIGRATION_BASELINE_FROZEN = "migration_baseline_frozen"
    DDL_SNAPSHOT_EXPORTED = "ddl_snapshot_exported"
    OPENAPI_SNAPSHOT_CAPTURED = "openapi_snapshot_captured"
    PERMISSION_MATRIX_FROZEN = "permission_matrix_frozen"
    RLS_BASELINE_FROZEN = "rls_baseline_frozen"
    SEC_CERT_ARCHIVED = "sec_cert_archived"
    PROD_DOSSIER_ARCHIVED = "prod_dossier_archived"
    TEST_RESULT_ARCHIVED = "test_result_archived"
    PERF_BASELINE_ARCHIVED = "perf_baseline_archived"
    IMAGE_LOCKED = "image_locked"
    CONFIG_BASELINE_FROZEN = "config_baseline_frozen"
    BACKUP_EVIDENCE_ARCHIVED = "backup_evidence_archived"
    DR_EVIDENCE_ARCHIVED = "dr_evidence_archived"
    ROLLBACK_PLAN_FROZEN = "rollback_plan_frozen"
    CORE_FREEZE_DECLARATION_EFFECTIVE = "core_freeze_declaration_effective"
    SEAL_REPORT_ASSEMBLED = "seal_report_assembled"
    SEAL_REPORT_CO_SIGNED = "seal_report_co_signed"
    SEAL_FINAL_PASS = "seal_final_pass"
    SEAL_FINAL_FAIL = "seal_final_fail"
    UNFREEZE_REQUESTED = "unfreeze_requested"
    UNFREEZE_APPROVED = "unfreeze_approved"

    SETTLEMENT_CREATED = "settlement_created"
    SETTLEMENT_CONFIRMED = "settlement_confirmed"
    SETTLEMENT_SETTLED = "settlement_settled"
    SETTLEMENT_CANCELLED = "settlement_cancelled"
    PAYMENT_REQUESTED = "payment_requested"
    PAYMENT_APPROVED = "payment_approved"
    PAYMENT_EXECUTING = "payment_executing"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    RECEIPT_CONFIRMED = "receipt_confirmed"
    RECEIPT_WRITE_OFF = "receipt_write_off"
    INVOICE_ISSUED = "invoice_issued"
    INVOICE_MATCHED = "invoice_matched"
    INVOICE_VERIFIED = "invoice_verified"
    INVOICE_ARCHIVED = "invoice_archived"
    INVOICE_VOID = "invoice_void"
    RECON_BATCH_CREATED = "recon_batch_created"
    RECON_DIFFERENCE_HANDLED = "recon_difference_handled"
    AR_VOUCHER_GENERATED = "ar_voucher_generated"
    AP_VOUCHER_GENERATED = "ap_voucher_generated"
    GL_VOUCHER_POSTED = "gl_voucher_posted"
    GL_PERIOD_CLOSED = "gl_period_closed"
    GL_RED_VOUCHER_CREATED = "gl_red_voucher_created"
    TREASURY_TRANSFER_EXECUTED = "treasury_transfer_executed"
    TREASURY_FREEZED = "treasury_freezed"
    TREASURY_UNFREEZED = "treasury_unfrozen"
    COLLECTION_TASK_GENERATED = "collection_task_generated"
    FIN_CORE_FREEZE_VIOLATION = "fin_core_freeze_violation"


@dataclass(frozen=True)
class AuditEntry:
    """审计日志条目 - 不可篡改。

    每条记录包含：租户、操作人、动作、目标实体、前后值、时间戳。
    """

    id: UUID
    tenant_id: UUID
    user_id: UUID | None
    action: AuditAction
    entity_type: str
    entity_id: str
    old_value: dict | None
    new_value: dict | None
    ip_address: str | None
    occurred_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        user_id: UUID | None,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        old_value: dict | None = None,
        new_value: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry:
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            occurred_at=datetime.now(timezone.utc),
        )