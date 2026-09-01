import { useState } from 'react'
import { Card, Button, Table, Tag, Statistic, Space, message } from 'antd'
import { secApi } from '@/api/sec'

export default function SecRedisScanPage() {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const handleScan = async () => {
    setLoading(true)
    try {
      const resp = await secApi.scanRedisKeys()
      setResult(resp.data)
      message.success('扫描完成')
    } catch { message.error('扫描失败') }
    finally { setLoading(false) }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Card title="Redis Key 扫描" extra={<Button type="primary" loading={loading} onClick={handleScan}>开始扫描</Button>}>
        {result && (
          <Space size="large">
            <Statistic title="总Key数" value={result.total_keys} />
            <Statistic title="违规数" value={result.violations?.length || 0} valueStyle={{ color: result.violations?.length ? 'red' : 'green' }} />
            <Statistic title="合规率" value={(result.compliance_rate * 100).toFixed(2)} suffix="%" />
          </Space>
        )}
      </Card>
      {result?.violations && (
        <Card title="违规键清单">
          <Table dataSource={result.violations} rowKey="violation_key" columns={[
            { title: 'Key', dataIndex: 'violation_key' },
            { title: '违规类型', dataIndex: 'violation_type', render: (v: string) => <Tag color="red">{v}</Tag> },
            { title: '期望前缀', dataIndex: 'expected_prefix' },
            { title: '实际前缀', dataIndex: 'actual_prefix' },
          ]} />
        </Card>
      )}
    </Space>
  )
}