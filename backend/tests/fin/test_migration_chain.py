"""迁移链测试 - 070-079 FIN 迁移完整性。

覆盖：
- 070-079 revision 链（down_revision 链接）
- 21 个 fin_* 表全部创建
- CHECK 约束（AR/AP 金额守恒、treasury 可用余额守恒、调拨不同账户）
- append-only 触发器（invoice archived、recon diff handle、collection record、GL period closed）
- RLS 策略（租户隔离 + 平台管理员豁免 + 跨租户结算互访）
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest

VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"

_MIGRATION_FILES = {
    "070": "070_fin_settlement.py",
    "071": "071_fin_payment.py",
    "072": "072_fin_receipt.py",
    "073": "073_fin_invoice.py",
    "074": "074_fin_reconciliation.py",
    "075": "075_fin_voucher.py",
    "076": "076_fin_gl.py",
    "077": "077_fin_treasury.py",
    "078": "078_fin_collection_and_outbox.py",
    "079": "079_fin_indexes_and_roles.py",
}


def _load_migration(revision: str):
    filename = _MIGRATION_FILES[revision]
    path = VERSIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _upgrade_source(revision: str) -> str:
    mod = _load_migration(revision)
    return inspect.getsource(mod.upgrade)


@pytest.fixture(scope="module")
def migrations() -> dict[str, object]:
    return {rev: _load_migration(rev) for rev in _MIGRATION_FILES}


class MigrationChainTest:
    """070-07#079 revision 链完整性测试。"""

    def test_revisions_are_070_to_079(self, migrations) -> None:
        assert set(migrations) == {f"{i:03d}" for i in range(70, 80)}

    @pytest.mark.parametrize(
        "rev,down",
        [
            ("070", "069"),
            ("071", "070"),
            ("072", "071"),
            ("073", "072"),
            ("074", "073"),

            ("075", "074"),
            ("076", "075"),
            ("077", "076"),
            ("078", "077"),
            ("079", "078"),
        ],
    )
    def test_down_revision_chain(self, migrations, rev, down) -> None:
        mod = migrations[rev]
        assert mod.revision == rev
        assert mod.down_revision == down

    def test_chain_is_linear_no_branch(self, migrations) -> None:
        revisions = [migrations[r].revision for r in sorted(_MIGRATION_FILES)]
        assert revisions == [f"{i:03d}" for i in range(70, 80)]
        down_revisions = [migrations[r].down_revision for r in sorted(_MIGRATION_FILES)]
        # 070 的 down 是 069（非 fin），其余形成 070→079 线性链
        assert down_revisions[0] == "069"
        assert down_revisions[1:] == [f"{i:03d}" for i in range(70, 79)]


class FinTablesTest:
    """21 个 fin_* 表创建测试。"""

    _EXPECTED_TABLES = {
        "fin_settlement",
        "fin_settlement_line",
        "fin_payment",
        "fin_receipt",
        "fin_receipt_writeoff_line",
        "fin_invoice",
        "fin_invoice_line",
        "fin_reconciliation",
        "fin_reconciliation_line",
        "fin_reconciliation_difference",
        "fin_recon_diff_handle_record",
        "fin_ar_voucher",
        "fin_ap_voucher",
        "fin_gl_account",
        "fin_gl_voucher",
        "fin_gl_voucher_line",
        "fin_treasury_account",
        "fin_treasury_transfer",
        "fin_collection_task",
        "fin_collection_record",
        "fin_event_outbox",
    }

    def test_total_fin_tables_is_21(self) -> None:
        all_source = "\n".join(_upgrade_source(r) for r in _MIGRATION_FILES)
        created = set()
        for line in all_source.splitlines():
            stripped = line.strip().upper()
            if stripped.startswith("CREATE TABLE FIN_"):
                table = stripped.split()[2].rstrip("(").lower()
                created.add(table)
        assert created == self._EXPECTED_TABLES
        assert len(created) == 21

    def test_each_expected_table_created(self) -> None:
        all_source = "\n".join(_upgrade_source(r) for r in _MIGRATION_FILES)
        for table in self._EXPECTED_TABLES:
            assert f"CREATE TABLE {table}" in all_source, f"{table} 未创建"


class CheckConstraintsTest:
    """CHECK 约束测试 - AR/AP 金额守恒、treasury 可用余额守恒。"""

    def test_ar_amount_conservation_check(self) -> None:
        src = _upgrade_source("075")
        assert "ck_fin_ar_amount_conserved" in src
        assert "receivable_amount = received_amount + unreceived_amount" in src

    def test_ap_amount_conservation_check(self) -> None:
        src = _upgrade_source("075")
        assert "ck_fin_ap_amount_conserved" in src
        assert "payable_amount = paid_amount + unpaid_amount" in src

    def test_treasury_available_balance_check(self) -> None:
        src = _upgrade_source("077")
        assert "ck_fin_treasury_available" in src
        assert "available_balance = balance - frozen_amount" in src

    def test_treasury_transfer_diff_accounts_check(self) -> None:
        src = _upgrade_source("077")
        assert "ck_fin_treasury_transfer_diff_accounts" in src
        assert "from_account_id <> to_account_id" in src


class AppendOnlyTriggersTest:
    """append-only 触发器测试。"""

    def test_invoice_archived_immutable_trigger(self) -> None:
        src = _upgrade_source("073")
        assert "trg_fin_invoice_archived_immutable" in src

    def test_recon_diff_handle_record_immutable_trigger(self) -> None:
        src = _upgrade_source("074")
        assert "trg_fin_recon_diff_handle_record_immutable" in src

    def test_collection_record_immutable_trigger(self) -> None:
        src = _upgrade_source("078")
        assert "trg_fin_collection_record_immutable" in src

    def test_gl_voucher_period_closed_immutable_trigger(self) -> None:
        src = _upgrade_source("076")
        assert "trg_fin_gl_voucher_period_closed_immutable" in src


class RlsPoliciesTest:
    """RLS 策略测试 - 租户隔离 + 平台管理员豁免 + 跨租户结算。"""

    def test_all_fin_migrations_enable_rls(self) -> None:
        # 070-078 每个迁移都启用 RLS（070/071 手动，072-078 循环体）
        for rev in [f"{i:03d}" for i in range(70, 79)]:
            src = _upgrade_source(rev)
            assert "ENABLE ROW LEVEL SECURITY" in src, f"{rev} 未启用 RLS"
            assert "FORCE ROW LEVEL SECURITY" in src, f"{rev} 未强制 RLS"

    def test_tenant_isolation_policies(self) -> None:
        # 070/071 手动写具体策略名，072-078 用 rls_{tbl}_tenant 循环模板
        src070 = _upgrade_source("070")
        src071 = _upgrade_source("071")
        assert "rls_fin_settlement_tenant" in src070
        assert "rls_fin_payment_tenant" in src071
        for rev in [f"{i:03d}" for i in range(72, 79)]:
            src = _upgrade_source(rev)
            assert "rls_" in src and "_tenant" in src, f"{rev} 缺少租户隔离策略"

    def test_platform_admin_exemption_policies(self) -> None:
        all_source = "\n".join(_upgrade_source(r) for r in _MIGRATION_FILES)
        assert "rls_fin_settlement_platform_admin" in all_source
        assert "rls_fin_payment_platform_admin" in all_source
        assert "app.is_platform_admin" in all_source

    def test_cross_tenant_settlement_policy(self) -> None:
        src = _upgrade_source("070")
        assert "rls_fin_settlement_cross_tenant" in src
        assert "initiator_tenant_id" in src
        assert "receiver_tenant_id" in src
        assert "FOR SELECT" in src