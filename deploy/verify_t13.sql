SELECT version_num FROM alembic_version;
SELECT count(*) AS mdm_table_count FROM information_schema.tables WHERE table_name LIKE 'mdm_%';
SELECT count(*) AS mdm_permission_count FROM iam_permission WHERE module = 'mdm';
SELECT count(*) AS rls_policy_count FROM pg_policies WHERE policyname LIKE 'rls_mdm_%';
