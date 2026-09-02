import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Input, Space } from 'antd'
import { pltApi } from '@/api/platform'

export default function TenantLifecyclePage() {
  const [tenantId, setTenantId] = useState('')
  const [data, setData] = useState<any>({})

  const load = () => { if (tenantId) pltApi.tenant.lifecycle(tenantId).then(resp => setData(resp.data)) }

  return (
    <Card title="租户生命周期管理">
      <Space style={{ marginBottom: 16 }}>
        <Input placeholder="租户 ID" value={tenantId} onChange={e => setTenantId(e.target.value)} style={{ width: 300 }} />
        <Button onClick={load}>查询</Button>
        <Button onClick={() => pltApi.tenant.freeze({ tenant_id: tenantId, reason: 'manual' })}>冻结</Button>
        <Button onClick={() => pltApi.tenant.unfreeze({ tenant_id: tenantId, reason: 'manual' })}>解冻</Button>
        <Button onClick={() => pltApi.tenant.archive({ tenant_id: tenantId, reason: 'manual' })}>归档</Button>
      </Space>
      <Card type="inner" title="当前状态">
        <Tag color={data.state === 'ACTIVE' ? 'green' : data.state === 'FROZEN' ? 'orange' : 'red'}>{data.state || '未知'}</Tag>
      </Card>
    </Card>
  )
}