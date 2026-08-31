"""批量上传 T13 迁移文件到服务器。"""
import subprocess
import sys
from pathlib import Path

FILES = [
    "backend/alembic/versions/020_mdm_group_catalog_tables.py",
    "backend/alembic/versions/021_mdm_enterprise_product_tables.py",
    "backend/alembic/versions/022_mdm_template_tables.py",
    "backend/alembic/versions/023_mdm_governance_tables.py",
    "backend/alembic/versions/024_mdm_negative_policy_audit_table.py",
    "backend/alembic/versions/025_mdm_master_data_audit_table.py",
    "backend/alembic/versions/026_mdm_inv_ledger_trigger_guard.py",
    "backend/alembic/versions/027_mdm_rls_policies.py",
]

for f in FILES:
    remote = f"/home/debian/EITP/{f}"
    result = subprocess.run(
        [sys.executable, "deploy/ssh_upload.py", f, remote],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"FAILED: {f}")
        print(result.stderr)
    else:
        print(f"  uploaded: {f}")

print("Batch upload complete")