import { useState } from 'react'
import { Card, Button, Alert, Input, Space } from 'antd'
import { pltApi } from '@/api/platform'

export default function AuditTamperCheckPage() {
  const [tenantId, setTenantId] = useState('')
  const [result, setResult] = useState<any>()

  const handleCheck = () => {
    pltApi.audit.tamperCheck({ tenant_id: tenantId }).then(resp => setResult(resp.data))
  }

  return (
    <Card title="审计哈希链篡改检测">
      <Space style={{ marginBottom: 16 }}>
        <Input placeholder="租户 ID" value={tenantId} onChange={e => setTenantId(e.target.value)} style={{ width: 300 }} />
        <Button type="primary" onClick={handleCheck}>执行检测</Button>
      </Space>
      {result && (
        <Alert
          type={result.verified ? 'success' : 'error'}
          message={result.verified ? '哈希链校验通过' : '检测到篡改'}
          description={result.tampered_positions?.length > 0 ? `篡改位置: ${result.tampered_positions.join(', ')}` : undefined}
        />
      )}
    </Card>
  )
}