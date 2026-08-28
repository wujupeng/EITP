use anyhow::Result;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Serialize)]
struct TaskRequest {
    task_type: String,
    tenant_id: Uuid,
}

#[derive(Debug, Deserialize)]
struct TaskResponse {
    task_id: Uuid,
    status: String,
}

pub struct ControlPlaneConnection {
    client: Client,
    base_url: String,
    platform_token: String,
}

impl ControlPlaneConnection {
    pub fn new(base_url: String, platform_token: String) -> Self {
        Self {
            client: Client::new(),
            base_url,
            platform_token,
        }
    }

    pub async fn report_task_complete(&self, task_id: Uuid, result: &str) -> Result<()> {
        let url = format!("{}/api/v1/agent/tasks/{}/complete", self.base_url, task_id);
        self.client
            .post(&url)
            .header("X-Platform-Token", &self.platform_token)
            .json(&serde_json::json!({ "result": result }))
            .send()
            .await?;
        Ok(())
    }

    pub async fn report_task_failed(&self, task_id: Uuid, error: &str) -> Result<()> {
        let url = format!("{}/api/v1/agent/tasks/{}/failed", self.base_url, task_id);
        self.client
            .post(&url)
            .header("X-Platform-Token", &self.platform_token)
            .json(&serde_json::json!({ "error": error }))
            .send()
            .await?;
        Ok(())
    }
}