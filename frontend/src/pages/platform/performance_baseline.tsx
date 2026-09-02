import { useState, useEffect } from 'react'
import { Card, Table, Tag, Alert } from 'antd'
import { pltApi } from '@/api/platform'

export default function PerformanceBaselinePage() {
  const [baselines, setBaselines] = useState<any[]>([])
  const [regression, setRegression] = useState<any>({})

  useEffect(() => {
    pltApi.performance.baselines().then(resp => setBaselines(resp.data.items || []))
    pltApi.performance.regressionCheck().then(resp => setRegression(resp.data))
  }, [])

  return (
    <Card title="性能基线管理">
      {regression.has_regression && <Alert type="error" message="检测到性能回归" style={{ marginBottom: 16 }} />}
      <Table dataSource={baselines} rowKey="baseline_id" columns={[
        { title: 'API路径', dataIndex: 'api_path' },
        { title: 'P95 (ms)', dataIndex: 'p95_ms' },
        { title: 'P99 (ms)', dataIndex: 'p99_ms' },
        { title: 'QPS', dataIndex: 'qps' },
      ]} />
    </Card>
  )
}