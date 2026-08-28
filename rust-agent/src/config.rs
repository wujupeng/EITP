use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct Config {
    pub control_plane_url: String,
    pub platform_token: String,
    pub postgres_url: String,
    pub backup_storage_path: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            control_plane_url: "http://localhost:8090".to_string(),
            platform_token: "change-me".to_string(),
            postgres_url: "postgres://eitp:eitp@localhost:5432/eitp".to_string(),
            backup_storage_path: "./backups".to_string(),
        }
    }
}

impl Config {
    pub fn load() -> anyhow::Result<Self> {
        let config_str = std::fs::read_to_string("agent.toml").unwrap_or_default();
        if config_str.is_empty() {
            return Ok(Self::default());
        }
        let config: Config = toml::from_str(&config_str)?;
        Ok(config)
    }
}