import { client } from '../client'

export interface GoldenPathReport {
  all_passed: boolean
  total_steps: number
  passed_steps: number
  failed_steps: number
  steps: Array<{ step: string; passed: boolean; message?: string }>
}

export interface LedgerTriggerVerifyResult {
  trigger_exists: boolean
  revoke_applied: boolean
  message: string
}

export interface IdempotencyVerifyResult {
  db_fact_layer: boolean
  redis_performance_layer: boolean
  fail_open: boolean
  message: string
}

export const e2eApi = {
  async runGoldenPath(): Promise<GoldenPathReport> {
    const { data } = await client.post('/admin/e2e/golden-path:run')
    return data
  },

  async verifyLedgerTrigger(): Promise<LedgerTriggerVerifyResult> {
    const { data } = await client.post('/admin/e2e/ledger-trigger:verify')
    return data
  },

  async verifyIdempotencyFailSafe(): Promise<IdempotencyVerifyResult> {
    const { data } = await client.post('/admin/e2e/idempotency-fail-safe:verify')
    return data
  },

  async getGoldenPathStatus(): Promise<{ e2e_enabled: boolean; total_steps: number }> {
    const { data } = await client.get('/admin/e2e/golden-path:status')
    return data
  },
}