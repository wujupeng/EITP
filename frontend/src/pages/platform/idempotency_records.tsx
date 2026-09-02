import { useState, useEffect } from 'react'
import { Card, Table, Input } from 'antd'
import { pltApi } from '@/api/platform'

export default function IdempotencyRecordsPage() {
  const [records, setRecords] = useState<any[]>([])
  const [tenantId, setTenantId] = useState('')

  useEffect(() => {
    if (tenantId) pltApi.idempotency.records({ tenant_id: tenantId }).then(resp => setRecords(resp.data.items || []))
  }, [tenantId])

  return (
    <Card title="幂等记录管理">
      <Input placeholder="租户 ID" value={tenantId} onChange={e => setTenantId(e.target.value)} style={{ width: 300, marginBottom: 16 }} />
      <Table dataSource={records} rowKey="idempotency_key" columns={[
        { title: '幂等键', dataIndex: 'idempotency_key' },
        { title: '请求哈希', dataIndex: 'request_hash' },
        { title: '响应状态', dataIndex: 'response_status' },
        { title: '创建时间', dataIndex: 'created_at' },
        { title: '过期时间', dataIndex: 'expires_at' },
      ]} />
    </Card>
  )
}