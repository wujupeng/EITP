import { useState, useEffect } from 'react'
import { Card, Descriptions, Input, Button } from 'antd'
import { pltApi } from '@/api/platform'

export default function TenantQuotaPage() {
  const [tenantId, setTenantId] = useState('')
  const [quota, setQuota] = useState<any>({})

  useEffect(() => { if (tenantId) pltApi.tenant.quota(tenantId).then(resp => setQuota(resp.data)) }, [tenantId])

  return (
    <Card title="租户配额管理">
      <Input placeholder="租户 ID" value={tenantId} onChange={e => setTenantId(e.target.value)} style={{ width: 300, marginBottom: 16 }} />
      <Descriptions bordered column={2}>
        <Descriptions.Item label="最大用户数">{quota.max_users}</Descriptions.Item>
        <Descriptions.Item label="每日订单上限">{quota.max_orders_per_day}</Descriptions.Item>
        <Descriptions.Item label="存储上限 (MB)">{quota.max_storage_mb}</Descriptions.Item>
        <Descriptions.Item label="每分钟API调用上限">{quota.max_api_calls_per_minute}</Descriptions.Item>
        <Descriptions.Item label="最大并发请求">{quota.max_concurrent_requests}</Descriptions.Item>
      </Descriptions>
    </Card>
  )
}