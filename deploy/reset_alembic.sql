DROP TRIGGER IF EXISTS trg_inv_ledger_no_update ON inv_inventory_ledger;
DROP TRIGGER IF EXISTS trg_inv_ledger_no_delete ON inv_inventory_ledger;
DROP TRIGGER IF EXISTS trg_inv_audit_no_update ON inv_inventory_audit;
DROP TRIGGER IF EXISTS trg_inv_audit_no_delete ON inv_inventory_audit;
DROP FUNCTION IF EXISTS fn_inv_ledger_append_only_guard() CASCADE;
UPDATE alembic_version SET version_num = '010';
SELECT version_num FROM alembic_version;
