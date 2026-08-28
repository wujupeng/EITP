mod backup;
mod config;
mod connection;
mod migration;

use anyhow::Result;
use tracing_subscriber;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();

    let cfg = config::Config::load()?;
    tracing::info!("EITP Rust Agent 启动");
    tracing::info!("控制面地址: {}", cfg.control_plane_url);

    let backup_executor = backup::BackupExecutor::new(cfg.backup_storage_path.clone());
    let migration_executor = migration::MigrationExecutor::new();
    let _conn = connection::ControlPlaneConnection::new(
        cfg.control_plane_url.clone(),
        cfg.platform_token.clone(),
    );

    tracing::info!("Agent 就绪，等待控制面调度");

    // T10/T09 阶段将实现完整的任务监听循环
    // 当前为骨架，仅验证编译与启动
    let test_tenant = uuid::Uuid::new_v4();
    let _ = backup_executor.backup_tenant(test_tenant).await;
    let _ = migration_executor
        .migrate_tenant(test_tenant, "shared_db", "dedicated_db")
        .await;

    tracing::info!("Agent 骨架验证完成");
    Ok(())
}